import pytest
from unittest.mock import patch
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from src.llm_config import get_chat_llm

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

