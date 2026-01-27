"""Tests for OpenRouterLLM implementation."""

import pytest

from minicode.llm import OpenRouterLLM


class TestOpenRouterLLM:
    """Test OpenRouterLLM class."""

    def test_initialization(self):
        """Test OpenRouterLLM initialization."""
        llm = OpenRouterLLM(api_key="test_key", model="anthropic/claude-3.5-haiku")

        assert llm.model == "anthropic/claude-3.5-haiku"
        assert str(llm.client.base_url).rstrip("/") == "https://openrouter.ai/api/v1"

    def test_convert_tool_messages_to_user_simple(self):
        """Test conversion of tool messages to user messages."""
        llm = OpenRouterLLM(api_key="test")

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "tool", "content": '{"result": "success"}', "name": "test_tool"},
        ]

        converted = llm._convert_tool_messages_to_user(messages)

        assert len(converted) == 3
        assert converted[0]["role"] == "user"
        assert converted[1]["role"] == "assistant"
        assert converted[2]["role"] == "user"
        assert "[Tool Result from test_tool]" in converted[2]["content"]
        assert '{"result": "success"}' in converted[2]["content"]

    def test_convert_tool_messages_preserves_non_tool(self):
        """Test that non-tool messages are preserved."""
        llm = OpenRouterLLM(api_key="test")

        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant message"},
        ]

        converted = llm._convert_tool_messages_to_user(messages)

        assert len(converted) == 3
        assert converted[0] == {"role": "system", "content": "System prompt"}
        assert converted[1] == {"role": "user", "content": "User message"}
        assert converted[2] == {"role": "assistant", "content": "Assistant message"}

    def test_convert_tool_messages_with_tool_calls(self):
        """Test conversion with assistant tool calls."""
        llm = OpenRouterLLM(api_key="test")

        messages = [
            {"role": "user", "content": "Read a file"},
            {
                "role": "assistant",
                "content": "I'll read it",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": {"path": "test.txt"}},
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"success": true, "content": "File contents"}',
                "tool_call_id": "call_123",
                "name": "read_file",
            },
        ]

        converted = llm._convert_tool_messages_to_user(messages)

        assert len(converted) == 3
        assert converted[0]["role"] == "user"
        assert converted[1]["role"] == "assistant"
        assert "tool_calls" in converted[1]
        assert converted[2]["role"] == "user"
        assert "[Tool Result from read_file]" in converted[2]["content"]
        assert "File contents" in converted[2]["content"]

    def test_convert_tool_messages_multiple_tools(self):
        """Test conversion with multiple tool results."""
        llm = OpenRouterLLM(api_key="test")

        messages = [
            {"role": "user", "content": "Do something"},
            {"role": "tool", "content": "Result 1", "name": "tool1"},
            {"role": "tool", "content": "Result 2", "name": "tool2"},
            {"role": "assistant", "content": "Done"},
        ]

        converted = llm._convert_tool_messages_to_user(messages)

        assert len(converted) == 4
        assert converted[0]["role"] == "user"
        assert converted[1]["role"] == "user"
        assert "[Tool Result from tool1]" in converted[1]["content"]
        assert converted[2]["role"] == "user"
        assert "[Tool Result from tool2]" in converted[2]["content"]
        assert converted[3]["role"] == "assistant"

    def test_convert_tool_messages_unknown_tool_name(self):
        """Test conversion when tool name is missing."""
        llm = OpenRouterLLM(api_key="test")

        messages = [
            {"role": "tool", "content": "Result without name"},
        ]

        converted = llm._convert_tool_messages_to_user(messages)

        assert len(converted) == 1
        assert converted[0]["role"] == "user"
        assert "[Tool Result from unknown]" in converted[0]["content"]

    def test_convert_tool_messages_empty_content(self):
        """Test conversion with empty tool content."""
        llm = OpenRouterLLM(api_key="test")

        messages = [
            {"role": "tool", "name": "test_tool"},
        ]

        converted = llm._convert_tool_messages_to_user(messages)

        assert len(converted) == 1
        assert converted[0]["role"] == "user"
        assert "[Tool Result from test_tool]" in converted[0]["content"]

    def test_convert_tool_messages_does_not_modify_original(self):
        """Test that conversion doesn't modify original messages."""
        llm = OpenRouterLLM(api_key="test")

        original_messages = [
            {"role": "tool", "content": "Test", "name": "tool1"},
        ]

        # Make a copy to compare
        original_copy = [msg.copy() for msg in original_messages]

        converted = llm._convert_tool_messages_to_user(original_messages)

        # Original should be unchanged
        assert original_messages == original_copy
        # Converted should be different
        assert converted[0]["role"] == "user"

    def test_default_model(self):
        """Test default model is set correctly."""
        llm = OpenRouterLLM(api_key="test")
        assert llm.model == "anthropic/claude-3.5-haiku"

    def test_custom_model(self):
        """Test custom model can be set."""
        llm = OpenRouterLLM(api_key="test", model="anthropic/claude-3-opus")
        assert llm.model == "anthropic/claude-3-opus"

    def test_provider_single_string(self):
        """Test provider with single string."""
        llm = OpenRouterLLM(api_key="test", provider="anthropic")

        provider_params = llm._build_provider_params()

        assert provider_params is not None
        assert provider_params["only"] == ["anthropic"]

    def test_provider_list(self):
        """Test provider with list of providers."""
        llm = OpenRouterLLM(api_key="test", provider=["anthropic", "amazon-bedrock"])

        provider_params = llm._build_provider_params()

        assert provider_params is not None
        assert provider_params["order"] == ["anthropic", "amazon-bedrock"]

    def test_provider_none(self):
        """Test provider with None (auto-routing)."""
        llm = OpenRouterLLM(api_key="test", provider=None)

        provider_params = llm._build_provider_params()

        assert provider_params is None

    def test_provider_allow_fallbacks_false(self):
        """Test provider with allow_fallbacks=False."""
        llm = OpenRouterLLM(api_key="test", provider="anthropic", allow_fallbacks=False)

        provider_params = llm._build_provider_params()

        assert provider_params is not None
        assert provider_params["only"] == ["anthropic"]
        assert provider_params["allow_fallbacks"] is False

    def test_provider_allow_fallbacks_true(self):
        """Test provider with allow_fallbacks=True (default)."""
        llm = OpenRouterLLM(api_key="test", provider="anthropic", allow_fallbacks=True)

        provider_params = llm._build_provider_params()

        assert provider_params is not None
        assert "allow_fallbacks" not in provider_params  # Only added when False
