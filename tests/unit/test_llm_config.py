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
