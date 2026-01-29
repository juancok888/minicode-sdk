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
            {"role": "tool", "content": '{"result": "success"}', "tool_name": "test_tool"},
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
                "tool_name": "read_file",
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
            {"role": "tool", "content": "Result 1", "tool_name": "tool1"},
            {"role": "tool", "content": "Result 2", "tool_name": "tool2"},
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
            {"role": "tool", "tool_name": "test_tool"},
        ]

        converted = llm._convert_tool_messages_to_user(messages)

        assert len(converted) == 1
        assert converted[0]["role"] == "user"
        assert "[Tool Result from test_tool]" in converted[0]["content"]

    def test_convert_tool_messages_does_not_modify_original(self):
        """Test that conversion doesn't modify original messages."""
        llm = OpenRouterLLM(api_key="test")

        original_messages = [
            {"role": "tool", "content": "Test", "tool_name": "tool1"},
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

    def test_convert_image_tool_result_to_multimodal(self):
        """Test conversion of image tool result to multimodal message."""
        import json

        llm = OpenRouterLLM(api_key="test")

        # Simulate an image tool result.
        image_result = {
            "success": True,
            "type": "image",
            "mime_type": "image/png",
            "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "path": "/path/to/image.png",
            "size": 1234,
        }

        messages = [
            {"role": "user", "content": "Read the image"},
            {"role": "tool", "content": json.dumps(image_result), "tool_name": "read_file"},
        ]

        converted = llm._convert_tool_messages_to_user(messages)

        assert len(converted) == 2
        assert converted[0]["role"] == "user"
        assert converted[1]["role"] == "user"

        # Check multimodal content structure.
        content = converted[1]["content"]
        assert isinstance(content, list)
        assert len(content) == 2

        # Check text block.
        assert content[0]["type"] == "text"
        assert "[Tool Result from read_file]" in content[0]["text"]
        assert "/path/to/image.png" in content[0]["text"]

        # Check image block.
        assert content[1]["type"] == "image_url"
        assert "image_url" in content[1]
        assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")

    def test_convert_image_tool_result_preserves_text_results(self):
        """Test that text tool results are still converted correctly."""
        import json

        llm = OpenRouterLLM(api_key="test")

        # Simulate a text tool result.
        text_result = {
            "success": True,
            "type": "text",
            "data": "Hello, World!",
            "path": "/path/to/file.txt",
            "size": 13,
        }

        messages = [
            {"role": "tool", "content": json.dumps(text_result), "tool_name": "read_file"},
        ]

        converted = llm._convert_tool_messages_to_user(messages)

        assert len(converted) == 1
        assert converted[0]["role"] == "user"
        # Text result should be a simple string, not multimodal.
        assert isinstance(converted[0]["content"], str)
        assert "[Tool Result from read_file]" in converted[0]["content"]

    def test_convert_image_tool_result_without_data(self):
        """Test that image result without data is treated as text."""
        import json

        llm = OpenRouterLLM(api_key="test")

        # Simulate an image tool result without data (e.g., error case).
        image_result = {
            "success": False,
            "type": "image",
            "error": "File not found",
        }

        messages = [
            {"role": "tool", "content": json.dumps(image_result), "tool_name": "read_file"},
        ]

        converted = llm._convert_tool_messages_to_user(messages)

        assert len(converted) == 1
        assert converted[0]["role"] == "user"
        # Should be treated as text since no data.
        assert isinstance(converted[0]["content"], str)

    def test_parse_tool_content_valid_json(self):
        """Test _parse_tool_content with valid JSON."""
        llm = OpenRouterLLM(api_key="test")

        result = llm._parse_tool_content('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_tool_content_invalid_json(self):
        """Test _parse_tool_content with invalid JSON."""
        llm = OpenRouterLLM(api_key="test")

        result = llm._parse_tool_content("not json")
        assert result is None

    def test_parse_tool_content_none(self):
        """Test _parse_tool_content with None."""
        llm = OpenRouterLLM(api_key="test")

        result = llm._parse_tool_content(None)
        assert result is None

    def test_build_image_content_block(self):
        """Test _build_image_content_block creates correct structure."""
        llm = OpenRouterLLM(api_key="test")

        result = {
            "mime_type": "image/jpeg",
            "data": "base64encodeddata",
        }

        block = llm._build_image_content_block(result)

        assert block["type"] == "image_url"
        assert block["image_url"]["url"] == "data:image/jpeg;base64,base64encodeddata"

    def test_build_image_content_block_default_mime_type(self):
        """Test _build_image_content_block uses default mime type."""
        llm = OpenRouterLLM(api_key="test")

        result = {
            "data": "base64encodeddata",
        }

        block = llm._build_image_content_block(result)

        assert block["image_url"]["url"].startswith("data:image/png;base64,")

    def test_strip_tool_calls_with_placeholder(self):
        """Test that tool_calls are replaced with descriptive placeholder."""
        llm = OpenRouterLLM(api_key="test")

        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "read_file", "arguments": "{}"},
                    },
                    {
                        "id": "call_2",
                        "function": {"name": "bash", "arguments": "{}"},
                    },
                ],
            },
        ]

        converted = llm._strip_tool_calls_from_assistant_messages(messages)

        assert len(converted) == 1
        assert converted[0]["role"] == "assistant"
        assert "tool_calls" not in converted[0]
        assert "read_file" in converted[0]["content"]
        assert "bash" in converted[0]["content"]

    def test_convert_pdf_tool_result_to_multimodal(self):
        """Test conversion of PDF tool result to multimodal message."""
        import json

        llm = OpenRouterLLM(api_key="test")

        # Simulate a PDF tool result with 2 pages.
        pdf_result = {
            "success": True,
            "type": "pdf",
            "path": "/path/to/document.pdf",
            "size": 12345,
            "page_count": 2,
            "pages": [
                {
                    "page": 1,
                    "mime_type": "image/png",
                    "data": "base64page1data",
                },
                {
                    "page": 2,
                    "mime_type": "image/png",
                    "data": "base64page2data",
                },
            ],
        }

        messages = [
            {"role": "user", "content": "Read the PDF"},
            {"role": "tool", "content": json.dumps(pdf_result), "tool_name": "read_file"},
        ]

        converted = llm._convert_tool_messages_to_user(messages)

        assert len(converted) == 2
        assert converted[0]["role"] == "user"
        assert converted[1]["role"] == "user"

        # Check multimodal content structure.
        content = converted[1]["content"]
        assert isinstance(content, list)
        # Should have: header text + (page text + page image) * 2 = 5 blocks
        assert len(content) == 5

        # Check header text.
        assert content[0]["type"] == "text"
        assert "[Tool Result from read_file]" in content[0]["text"]
        assert "/path/to/document.pdf" in content[0]["text"]
        assert "2 pages" in content[0]["text"]

        # Check page 1.
        assert content[1]["type"] == "text"
        assert "Page 1" in content[1]["text"]
        assert content[2]["type"] == "image_url"
        assert "base64page1data" in content[2]["image_url"]["url"]

        # Check page 2.
        assert content[3]["type"] == "text"
        assert "Page 2" in content[3]["text"]
        assert content[4]["type"] == "image_url"
        assert "base64page2data" in content[4]["image_url"]["url"]

    def test_build_pdf_content_blocks(self):
        """Test _build_pdf_content_blocks creates correct structure."""
        llm = OpenRouterLLM(api_key="test")

        result = {
            "path": "/test.pdf",
            "size": 1000,
            "page_count": 1,
            "pages": [
                {"page": 1, "mime_type": "image/png", "data": "testdata"},
            ],
        }

        blocks = llm._build_pdf_content_blocks(result, "read_file")

        assert len(blocks) == 3  # header + page text + page image
        assert blocks[0]["type"] == "text"
        assert "/test.pdf" in blocks[0]["text"]
        assert "1 pages" in blocks[0]["text"]
        assert blocks[1]["type"] == "text"
        assert "Page 1" in blocks[1]["text"]
        assert blocks[2]["type"] == "image_url"

    def test_convert_pdf_without_pages_treated_as_text(self):
        """Test that PDF result without pages is treated as text."""
        import json

        llm = OpenRouterLLM(api_key="test")

        # Simulate a PDF error result.
        pdf_result = {
            "success": False,
            "type": "pdf",
            "error": "Failed to read PDF",
        }

        messages = [
            {"role": "tool", "content": json.dumps(pdf_result), "tool_name": "read_file"},
        ]

        converted = llm._convert_tool_messages_to_user(messages)

        assert len(converted) == 1
        assert converted[0]["role"] == "user"
        # Should be treated as text since no pages.
        assert isinstance(converted[0]["content"], str)
