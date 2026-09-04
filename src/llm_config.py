import os
from typing import List, Union
from google import genai
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableWithFallbacks
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

# Text-out models ordered: best/fastest first, stable fallbacks last.
# Source: Gemini API model list (updated 2026-08).
# Excluded: TTS, image-gen, video-gen, live-API, embeddings, robotics, agent-only models.
# NOTE: gemini-2.5-flash / gemini-2.5-flash-lite are NOT available to new users (404);
#       kept at the end as last-resort fallbacks in case access is granted later.
GEMINI_MODEL_CHAIN = [
    # ── Gemini Flash (primary workhorses – best latency / quality balance) ──
    "gemini-3.5-flash",        # Gemini 3.5 Flash       | text-out
    "gemini-3.6-flash",        # Gemini 3.6 Flash       | text-out
    "gemini-3-flash",          # Gemini 3 Flash         | text-out
    # ── Gemini Flash Lite (high-throughput, rate-limit relief) ──
    "gemini-3.1-flash-lite",   # Gemini 3.1 Flash Lite  | text-out
    "gemini-3.5-flash-lite",   # Gemini 3.5 Flash Lite  | text-out
    # ── Gemini 2.x and 1.x Stable (widely available) ──
    "gemini-2.0-flash",        # Gemini 2.0 Flash       | text-out
    "gemini-1.5-flash",        # Gemini 1.5 Flash       | text-out
    # ── Gemini Pro (highest quality – slower, use when Flash fails) ──
    "gemini-3.1-pro",          # Gemini 3.1 Pro         | text-out
    "gemini-2.5-pro",          # Gemini 2.5 Pro         | text-out
    "gemini-1.5-pro",          # Gemini 1.5 Pro         | text-out
    # ── Legacy / restricted (last-resort – may 404 for new API keys) ──
    "gemini-2.5-flash",        # Gemini 2.5 Flash       | text-out (restricted)
    "gemini-2.5-flash-lite",   # Gemini 2.5 Flash Lite  | text-out (restricted)
]

# Groq production models supporting function calling / tool use and high throughput.
# Verified against Groq API / docs (2026):
# Primary: llama-3.3-70b-versatile (128k context, high reasoning & tool use)
# Fallback: llama-3.1-8b-instant (128k context, fast, lightweight fallback)
GROQ_MODEL_CHAIN = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]


class ChatGoogleGenerativeAIWithEmptyCheck(ChatGoogleGenerativeAI):
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


def _build_gemini_chain(temperature: float = 0.3) -> List[BaseChatModel]:
    """
    Builds the list of ChatGoogleGenerativeAI models with empty check,
    request_timeout=45.0, and convert_system_message_to_human=True.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    llms = []
    for model in GEMINI_MODEL_CHAIN:
        llm = ChatGoogleGenerativeAIWithEmptyCheck(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
            convert_system_message_to_human=True,
            request_timeout=45.0,
        )
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

    llms = []
    for model in GROQ_MODEL_CHAIN:
        llm = ChatGroqWithEmptyCheck(
            model_name=model,
            groq_api_key=groq_api_key,
            temperature=temperature,
            request_timeout=45.0,
        )
        llms.append(llm)
    return llms


def _build_provider_chain(provider: str, temperature: float = 0.3) -> List[BaseChatModel]:
    normalized_provider = (provider or "").strip().lower()
    if normalized_provider == "groq":
        return _build_groq_chain(temperature=temperature)
    elif normalized_provider in ("gemini", ""):
        return _build_gemini_chain(temperature=temperature)
    else:
        raise ValueError(f"Unsupported LLM provider: '{provider}'. Supported providers: 'gemini', 'groq'.")


def get_chat_llm(temperature: float = 0.3) -> Union[BaseChatModel, RunnableWithFallbacks]:
    """
    Builds the primary + .with_fallbacks() chain for the configured LLM provider.
    Reads PRIMARY_LLM_PROVIDER (default: 'gemini').
    If FALLBACK_LLM_PROVIDER is set, chains the primary provider's models with the
    fallback provider's models in a single combined .with_fallbacks() call.
    """
    primary_provider = os.getenv("PRIMARY_LLM_PROVIDER", "gemini")
    primary_llms = _build_provider_chain(primary_provider, temperature=temperature)

    fallback_provider = os.getenv("FALLBACK_LLM_PROVIDER", "").strip()
    fallback_llms: List[BaseChatModel] = []
    if fallback_provider and fallback_provider.lower() != primary_provider.strip().lower():
        fallback_llms = _build_provider_chain(fallback_provider, temperature=temperature)

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
