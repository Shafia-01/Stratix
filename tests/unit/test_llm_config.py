import os
import pytest
from unittest.mock import patch
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.runnables import RunnableWithFallbacks
from src.llm_config import (
    get_chat_llm,
    ChatGoogleGenerativeAIWithEmptyCheck,
    ChatGroqWithEmptyCheck,
    GROQ_MODEL_CHAIN,
    GEMINI_MODEL_CHAIN,
)


@pytest.mark.unit
def test_llm_fallback_on_empty_response():
    """
    If the primary model returns an empty string or whitespace,
    the fallback chain should trigger and call the fallback model.
    """
    # Construct real LangChain response structures
    mock_empty_response = ChatResult(generations=[
        ChatGeneration(message=AIMessage(content="   "))
    ])

    mock_success_response = ChatResult(generations=[
        ChatGeneration(message=AIMessage(content="Success output"))
    ])

    # Patch the underlying _generate method
    with patch("langchain_google_genai.ChatGoogleGenerativeAI._generate") as mock_super_generate:
        mock_super_generate.side_effect = [mock_empty_response, mock_success_response]

        chain = get_chat_llm(temperature=0.3)
        res = chain.invoke([HumanMessage(content="test prompt")])

        assert res.content == "Success output"
        assert mock_super_generate.call_count == 2


@pytest.mark.unit
def test_llm_tool_call_empty_content_allowed():
    """
    If the response has tool_calls with empty text content, it should NOT trigger a fallback or raise ValueError.
    """
    tool_call_response = ChatResult(generations=[
        ChatGeneration(message=AIMessage(content="", tool_calls=[{"name": "test_tool", "args": {}, "id": "1"}]))
    ])

    with patch("langchain_google_genai.ChatGoogleGenerativeAI._generate") as mock_super_generate:
        mock_super_generate.return_value = tool_call_response

        chain = get_chat_llm(temperature=0.3)
        res = chain.invoke([HumanMessage(content="test prompt")])

        assert res.tool_calls == [{"name": "test_tool", "args": {}, "id": "1", "type": "tool_call"}]
        assert mock_super_generate.call_count == 1


@pytest.mark.unit
def test_groq_missing_api_key_fails_loudly(monkeypatch):
    """
    If PRIMARY_LLM_PROVIDER=groq but GROQ_API_KEY is missing/empty,
    get_chat_llm must raise a clear ValueError at startup.
    """
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GROQ_API_KEY environment variable is required"):
        get_chat_llm(temperature=0.3)


@pytest.mark.unit
def test_groq_provider_chain_construction(monkeypatch):
    """
    With PRIMARY_LLM_PROVIDER=groq and a valid GROQ_API_KEY,
    get_chat_llm constructs a chain of ChatGroqWithEmptyCheck models.
    """
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "mock_groq_key_123")

    chain = get_chat_llm(temperature=0.5)

    assert isinstance(chain, RunnableWithFallbacks)
    primary = chain.runnable
    assert isinstance(primary, ChatGroqWithEmptyCheck)
    assert primary.model_name == GROQ_MODEL_CHAIN[0]
    assert primary.temperature == 0.5

    # Check fallbacks
    fallbacks = chain.fallbacks
    assert len(fallbacks) == len(GROQ_MODEL_CHAIN) - 1
    assert all(isinstance(fb, ChatGroqWithEmptyCheck) for fb in fallbacks)
    assert fallbacks[0].model_name == GROQ_MODEL_CHAIN[1]


@pytest.mark.unit
def test_groq_fallback_on_empty_response(monkeypatch):
    """
    Test that ChatGroqWithEmptyCheck raises ValueError on empty content and triggers
    fallback to the next model in the Groq chain.
    """
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "mock_groq_key_123")

    mock_empty_response = ChatResult(generations=[
        ChatGeneration(message=AIMessage(content="   "))
    ])
    mock_success_response = ChatResult(generations=[
        ChatGeneration(message=AIMessage(content="Groq response output"))
    ])

    with patch("langchain_groq.ChatGroq._generate") as mock_groq_generate:
        mock_groq_generate.side_effect = [mock_empty_response, mock_success_response]

        chain = get_chat_llm(temperature=0.3)
        res = chain.invoke([HumanMessage(content="Hello Groq")])

        assert res.content == "Groq response output"
        assert mock_groq_generate.call_count == 2


@pytest.mark.unit
def test_groq_tool_call_empty_content_allowed(monkeypatch):
    """
    Groq model returning tool_calls with empty text content should NOT raise ValueError.
    """
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "mock_groq_key_123")

    tool_call_response = ChatResult(generations=[
        ChatGeneration(message=AIMessage(content="", tool_calls=[{"name": "search", "args": {"q": "python"}, "id": "call_1"}]))
    ])

    with patch("langchain_groq.ChatGroq._generate") as mock_groq_generate:
        mock_groq_generate.return_value = tool_call_response

        chain = get_chat_llm(temperature=0.3)
        res = chain.invoke([HumanMessage(content="search something")])

        assert len(res.tool_calls) == 1
        assert res.tool_calls[0]["name"] == "search"
        assert mock_groq_generate.call_count == 1


@pytest.mark.unit
def test_cross_provider_fallback_gemini_to_groq(monkeypatch):
    """
    PRIMARY_LLM_PROVIDER=gemini and FALLBACK_LLM_PROVIDER=groq
    combines Gemini models with Groq models in a single fallback chain.
    """
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("FALLBACK_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "mock_groq_key")

    chain = get_chat_llm(temperature=0.3)
    assert isinstance(chain, RunnableWithFallbacks)
    assert isinstance(chain.runnable, ChatGoogleGenerativeAIWithEmptyCheck)

    # Fallbacks include remaining Gemini models + Groq models
    expected_count = (len(GEMINI_MODEL_CHAIN) - 1) + len(GROQ_MODEL_CHAIN)
    assert len(chain.fallbacks) == expected_count
    assert isinstance(chain.fallbacks[-1], ChatGroqWithEmptyCheck)


@pytest.mark.unit
def test_unsupported_provider_raises_error(monkeypatch):
    """
    Unsupported provider name raises ValueError.
    """
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "unsupported_llm")
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        get_chat_llm(temperature=0.3)
