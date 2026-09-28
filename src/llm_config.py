import os
from typing import Any, List, Optional, Union
from google import genai
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableWithFallbacks
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

# Gemini production models ordered: high-capability primary reasoning first, fast lightweight fallback last.
# Primary: gemini-3.8-flash (1M+ context, primary reasoning, agent execution, structured output, tool calling)
# Fallback: gemini-3.5-flash-lite (fast inference, rate-limit relief, auxiliary/helper tasks)
GEMINI_MODEL_CHAIN = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
]

# Groq production models supporting function calling / tool use and high throughput.
# Primary: openai/gpt-oss-120b (high reasoning & tool use; official Groq replacement for llama-3.3-70b-versatile)
# Fallback: openai/gpt-oss-20b (fast, lightweight fallback; official Groq replacement for llama-3.1-8b-instant)
GROQ_MODEL_CHAIN = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]


def _get_gemini_models() -> List[str]:
    custom = os.getenv("GEMINI_MODEL") or os.getenv("GOOGLE_GEMINI_MODEL") or os.getenv("GOOGLE_MODEL") or os.getenv("PRIMARY_MODEL")
    if custom and custom.strip():
        models = [m.strip() for m in custom.split(",") if m.strip()]
        if len(models) == 1 and models[0] != "gemini-3.5-flash-lite":
            fb = os.getenv("FALLBACK_MODEL")
            if fb and fb.strip():
                models.append(fb.strip())
            else:
                models.append("gemini-3.5-flash-lite")
        return models
    return GEMINI_MODEL_CHAIN


def _get_groq_models() -> List[str]:
    custom = os.getenv("GROQ_MODEL") or os.getenv("GROQ_MODEL_NAME") or os.getenv("GROQ_LLM_MODEL")
    if custom and custom.strip():
        models = [m.strip() for m in custom.split(",") if m.strip()]
        if len(models) == 1 and models[0] != "openai/gpt-oss-20b":
            models.append("openai/gpt-oss-20b")
        return models
    return GROQ_MODEL_CHAIN


def _map_thinking_budget_to_level(thinking_budget: Union[int, str, None]) -> Optional[str]:
    """
    Map legacy thinking_budget to Gemini 3.8 thinking_level ('low', 'medium', 'high').
    Note: 'minimal' is NOT supported for Gemini 3.8.
    """
    if thinking_budget is None:
        return None
    if isinstance(thinking_budget, str):
        val = thinking_budget.strip().lower()
        if val in ("low", "medium", "high"):
            return val
        try:
            budget_num = int(val)
        except ValueError:
            return "medium"
    else:
        budget_num = int(thinking_budget)

    if budget_num <= 1024:
        return "low"
    elif budget_num <= 8192:
        return "medium"
    else:
        return "high"


class ChatGoogleGenerativeAIWithEmptyCheck(ChatGoogleGenerativeAI):
    def __init__(self, *args, **kwargs):
        # Support migration from legacy thinking_budget to thinking_level
        if "thinking_budget" in kwargs and not kwargs.get("thinking_level"):
            mapped_level = _map_thinking_budget_to_level(kwargs.pop("thinking_budget"))
            if mapped_level:
                kwargs["thinking_level"] = mapped_level
        super().__init__(*args, **kwargs)

    def _build_base_generation_config(self, stop: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
        """
        Build base generation config, enforcing Gemini 3.8 parameter compatibility.
        Gemini 3.8 does not support sampling parameters: temperature, top_p, top_k, candidate_count.
        """
        config = super()._build_base_generation_config(stop=stop, **kwargs)
        model_name = getattr(self, "model", "") or ""
        if model_name.startswith("gemini-3.8"):
            config.pop("temperature", None)
            config.pop("top_p", None)
            config.pop("top_k", None)
            config.pop("candidate_count", None)
        return config

    def _is_empty_and_no_tools(self, result) -> bool:
        if not result or not result.generations:
            return True
        gen = result.generations[0]
        msg = getattr(gen, "message", None)
        if msg is not None:
            if getattr(msg, "tool_calls", None) or getattr(msg, "invalid_tool_calls", None):
                return False
            if isinstance(getattr(msg, "additional_kwargs", None), dict) and msg.additional_kwargs.get("tool_calls"):
                return False
        text = gen.text if hasattr(gen, "text") else (getattr(msg, "content", "") if msg else "")
        return not text or not str(text).strip()

    def _generate(self, *args, **kwargs):
        result = super()._generate(*args, **kwargs)
        if self._is_empty_and_no_tools(result):
            model_name = getattr(self, "model", "unknown")
            raise ValueError(f"Empty LLM response content from {model_name}")
        return result

    async def _agenerate(self, *args, **kwargs):
        result = await super()._agenerate(*args, **kwargs)
        if self._is_empty_and_no_tools(result):
            model_name = getattr(self, "model", "unknown")
            raise ValueError(f"Empty LLM response content from {model_name}")
        return result


class ChatGroqWithEmptyCheck(ChatGroq):
    def _is_empty_and_no_tools(self, result) -> bool:
        if not result or not result.generations:
            return True
        gen = result.generations[0]
        msg = getattr(gen, "message", None)
        if msg is not None:
            if getattr(msg, "tool_calls", None) or getattr(msg, "invalid_tool_calls", None):
                return False
            if isinstance(getattr(msg, "additional_kwargs", None), dict) and msg.additional_kwargs.get("tool_calls"):
                return False
        text = gen.text if hasattr(gen, "text") else (getattr(msg, "content", "") if msg else "")
        return not text or not str(text).strip()

    def _generate(self, *args, **kwargs):
        result = super()._generate(*args, **kwargs)
        if self._is_empty_and_no_tools(result):
            model_name = getattr(self, "model_name", getattr(self, "model", "unknown"))
            raise ValueError(f"Empty LLM response content from {model_name}")
        return result

    async def _agenerate(self, *args, **kwargs):
        result = await super()._agenerate(*args, **kwargs)
        if self._is_empty_and_no_tools(result):
            model_name = getattr(self, "model_name", getattr(self, "model", "unknown"))
            raise ValueError(f"Empty LLM response content from {model_name}")
        return result


def _build_gemini_chain(
    temperature: float = 0.3,
    thinking_level: Optional[str] = None,
    thinking_budget: Optional[Union[int, str]] = None,
) -> List[BaseChatModel]:
    """
    Builds the list of ChatGoogleGenerativeAI models with empty check,
    request_timeout=45.0, and convert_system_message_to_human=True.

    For Gemini 3.8 (e.g. gemini-3.8-flash):
    - Sampling parameters (temperature, top_p, top_k, candidate_count) are omitted/stripped.
    - Thinking configuration is migrated to thinking_level ('low', 'medium', 'high').
    For other Gemini models (e.g. gemini-3.5-flash-lite):
    - Standard temperature and sampling parameters are preserved.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    models = _get_gemini_models()
    llms = []

    # Resolve thinking_level
    resolved_thinking_level = thinking_level
    if not resolved_thinking_level and thinking_budget is not None:
        resolved_thinking_level = _map_thinking_budget_to_level(thinking_budget)
    if not resolved_thinking_level:
        env_level = os.getenv("GEMINI_THINKING_LEVEL")
        env_budget = os.getenv("GEMINI_THINKING_BUDGET")
        if env_level and env_level.strip().lower() in ("low", "medium", "high"):
            resolved_thinking_level = env_level.strip().lower()
        elif env_budget:
            resolved_thinking_level = _map_thinking_budget_to_level(env_budget)

    for model in models:
        kwargs: dict = {
            "model": model,
            "google_api_key": api_key,
            "convert_system_message_to_human": True,
            "request_timeout": 45.0,
        }
        is_gemini_38 = model.startswith("gemini-3.8")
        if not is_gemini_38:
            kwargs["temperature"] = temperature
        else:
            kwargs["thinking_level"] = resolved_thinking_level or "medium"

        llm = ChatGoogleGenerativeAIWithEmptyCheck(**kwargs)
        llms.append(llm)
    return llms


def _build_groq_chain(temperature: float = 0.3) -> List[BaseChatModel]:
    """
    Builds the list of ChatGroq models with empty check and request_timeout=45.0.
    Fails loudly at startup if GROQ_API_KEY is not set.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key or not groq_api_key.strip():
        raise ValueError("GROQ_API_KEY environment variable is required when using Groq as an LLM provider.")

    models = _get_groq_models()
    llms = []
    for model in models:
        llm = ChatGroqWithEmptyCheck(
            model_name=model,
            groq_api_key=groq_api_key,
            temperature=temperature,
            request_timeout=45.0,
        )
        llms.append(llm)
    return llms


def _build_provider_chain(
    provider: str,
    temperature: float = 0.3,
    thinking_level: Optional[str] = None,
    thinking_budget: Optional[Union[int, str]] = None,
) -> List[BaseChatModel]:
    normalized_provider = (provider or "").strip().lower()
    if normalized_provider == "groq":
        return _build_groq_chain(temperature=temperature)
    elif normalized_provider in ("gemini", ""):
        return _build_gemini_chain(
            temperature=temperature,
            thinking_level=thinking_level,
            thinking_budget=thinking_budget,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: '{provider}'. Supported providers: 'gemini', 'groq'.")


def get_chat_llm(
    temperature: float = 0.3,
    thinking_level: Optional[str] = None,
    thinking_budget: Optional[Union[int, str]] = None,
) -> Union[BaseChatModel, RunnableWithFallbacks]:
    """
    Builds the primary + .with_fallbacks() chain for the configured LLM provider.
    Reads PRIMARY_LLM_PROVIDER (default: 'gemini').
    If FALLBACK_LLM_PROVIDER is set, chains the primary provider's models with the
    fallback provider's models in a single combined .with_fallbacks() call.
    """
    primary_provider = os.getenv("PRIMARY_LLM_PROVIDER", "gemini")
    primary_llms = _build_provider_chain(
        primary_provider,
        temperature=temperature,
        thinking_level=thinking_level,
        thinking_budget=thinking_budget,
    )

    fallback_provider = os.getenv("FALLBACK_LLM_PROVIDER", "").strip()
    fallback_llms: List[BaseChatModel] = []
    if fallback_provider and fallback_provider.lower() != primary_provider.strip().lower():
        fallback_llms = _build_provider_chain(
            fallback_provider,
            temperature=temperature,
            thinking_level=thinking_level,
            thinking_budget=thinking_budget,
        )

    all_llms = primary_llms + fallback_llms
    if not all_llms:
        raise ValueError("No LLM models configured in chain.")

    if len(all_llms) == 1:
        return all_llms[0]

    return all_llms[0].with_fallbacks(all_llms[1:])


_genai_client = None

def get_generation_llm():
    """
    Lazily creates and returns the google.genai.Client instance.
    """
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client()
    return _genai_client

