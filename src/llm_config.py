import os
from google import genai
from langchain_google_genai import ChatGoogleGenerativeAI

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
    # ── Gemini Pro (highest quality – slower, use when Flash fails) ──
    "gemini-3.1-pro",          # Gemini 3.1 Pro         | text-out
    "gemini-2.5-pro",          # Gemini 2.5 Pro         | text-out
    # ── Legacy / restricted (last-resort – may 404 for new API keys) ──
    "gemini-2.5-flash",        # Gemini 2.5 Flash       | text-out (restricted)
    "gemini-2.5-flash-lite",   # Gemini 2.5 Flash Lite  | text-out (restricted)
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
            raise ValueError(f"Empty LLM response content from {self.model}")
        return result

    async def _agenerate(self, *args, **kwargs):
        result = await super()._agenerate(*args, **kwargs)
        if self._is_empty_and_no_tools(result):
            raise ValueError(f"Empty LLM response content from {self.model}")
        return result

def get_chat_llm(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    """
    Builds the primary + .with_fallbacks() chain for ChatGoogleGenerativeAI
    with explicit request_timeout on every instance and empty content verification.
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

    return llms[0].with_fallbacks(llms[1:])

_genai_client = None

def get_generation_llm():
    """
    Lazily creates and returns the google.genai.Client instance.
    """
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client()
    return _genai_client
