"""OpenRouter LLM implementation with tool role conversion.

OpenRouter doesn't support role="tool" in messages, so we convert them to role="user".
Supports multimodal messages for image tool results.
"""

import json
import os
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from minicode.llm.openai import OpenAILLM


class OpenRouterLLM(OpenAILLM):
    """OpenRouter LLM implementation.

    This class extends OpenAILLM to handle OpenRouter's API limitations.
    OpenRouter doesn't support role="tool", so we convert tool results to user messages.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "anthropic/claude-3.5-haiku",
        provider: Optional[Union[str, List[str]]] = None,
        organization: Optional[str] = None,
        allow_fallbacks: bool = False,
    ):
        """Initialize OpenRouter LLM.

        Args:
            api_key: OpenRouter API key (if not provided, will use OPENROUTER_API_KEY env var)
            model: Model name to use (default: anthropic/claude-3.5-haiku)
            organization: Optional organization ID
            provider: Provider to use. Can be:
                - Single provider string: "anthropic", "amazon-bedrock", "google-vertex"
                - List of providers in priority order: ["anthropic", "amazon-bedrock"]
                - None (default): Let OpenRouter choose automatically
            allow_fallbacks: Whether to allow fallback to other providers (default: False)
        """
        # Initialize parent with OpenRouter base URL
        super().__init__(
            api_key=api_key,
            model=model,
            base_url="https://openrouter.ai/api/v1",
            organization=organization,
        )

        # Store provider preferences
        self.provider = provider
        self.allow_fallbacks = allow_fallbacks

    def _build_provider_params(self) -> Optional[Dict[str, Any]]:
        """Build provider routing parameters for OpenRouter API.

        Returns:
            Provider configuration dict, or None if no provider specified.
        """
        if self.provider is None:
            return None

        provider_config: Dict[str, Any] = {}

        # Handle single provider or list of providers
        if isinstance(self.provider, str):
            # Single provider: use "only" to restrict to this provider
            provider_config["only"] = [self.provider]
        else:
            # Multiple providers: use "order" for priority
            provider_config["order"] = self.provider

        # Add fallback setting
        if not self.allow_fallbacks:
            provider_config["allow_fallbacks"] = False

        return provider_config

    def _strip_tool_calls_from_assistant_messages(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Strip tool_calls from assistant messages.

        Since OpenRouter doesn't support tool responses, we need to remove tool_calls
        from assistant messages to maintain message format consistency.

        Args:
            messages: List of messages in OpenAI format.

        Returns:
            List of messages with tool_calls removed from assistant messages.
        """
        converted = []
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                new_msg = msg.copy()
                tool_calls = new_msg.pop("tool_calls")
                # Keep the content if it exists, otherwise provide a placeholder
                # describing which tools were called.
                if not new_msg.get("content"):
                    tool_names = [
                        tc.get("function", {}).get("name", "unknown")
                        for tc in tool_calls
                    ]
                    new_msg["content"] = f"[Called tools: {', '.join(tool_names)}]"
                converted.append(new_msg)
            else:
                converted.append(msg.copy())
        return converted

    def _parse_tool_content(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse tool result content as JSON.

        Args:
            content: Tool result content string.

        Returns:
            Parsed JSON dict, or None if parsing fails.
        """
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return None

    def _build_image_content_block(
        self, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build an image content block for multimodal messages.

        Args:
            result: Tool result containing image data.

        Returns:
            Image URL content block in OpenAI format.
        """
        mime_type = result.get("mime_type", "image/png")
        base64_data = result.get("data", "")
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64_data}",
            },
        }

    def _build_pdf_content_blocks(
        self, result: Dict[str, Any], tool_name: str
    ) -> List[Dict[str, Any]]:
        """Build content blocks for a PDF tool result.

        Each PDF page is converted to an image content block.

        Args:
            result: Tool result containing PDF pages data.
            tool_name: Name of the tool that produced the result.

        Returns:
            List of content blocks for multimodal message.
        """
        pdf_path = result.get("path", "unknown")
        pdf_size = result.get("size", 0)
        page_count = result.get("page_count", 0)
        pages = result.get("pages", [])

        content_blocks: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    f"[Tool Result from {tool_name}]\n"
                    f"PDF file: {pdf_path} ({pdf_size} bytes, {page_count} pages)\n"
                    "Pages are shown below:"
                ),
            }
        ]

        for page_data in pages:
            page_num = page_data.get("page", 0)
            content_blocks.append({
                "type": "text",
                "text": f"\n--- Page {page_num} ---",
            })
            content_blocks.append(self._build_image_content_block(page_data))

        return content_blocks

    def _convert_tool_messages_to_user(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert tool role messages to user role messages.

        OpenRouter doesn't support role="tool", so we convert them to role="user"
        with a formatted message indicating the tool result.

        For image tool results, creates multimodal messages with image content blocks
        so the model can "see" the image.

        For PDF tool results, creates multimodal messages with each page as an image.

        Args:
            messages: List of messages in OpenAI format.

        Returns:
            List of messages with tool roles converted to user roles.
        """
        converted = []
        for msg in messages:
            if msg.get("role") == "tool":
                tool_name = msg.get("tool_name", "unknown")
                content = msg.get("content", "")

                # Try to parse as JSON to check for image/pdf type.
                result = self._parse_tool_content(content)

                if result and result.get("type") == "pdf" and result.get("pages"):
                    # Build multimodal message with PDF page images.
                    user_msg = {
                        "role": "user",
                        "content": self._build_pdf_content_blocks(result, tool_name),
                    }
                elif result and result.get("type") == "image" and result.get("data"):
                    # Build multimodal message with image content block.
                    image_path = result.get("path", "unknown")
                    image_size = result.get("size", 0)
                    text_content = (
                        f"[Tool Result from {tool_name}]\n"
                        f"Image file: {image_path} ({image_size} bytes)\n"
                        "The image is shown below:"
                    )
                    user_msg = {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": text_content},
                            self._build_image_content_block(result),
                        ],
                    }
                else:
                    # Regular text tool result.
                    user_msg = {
                        "role": "user",
                        "content": f"[Tool Result from {tool_name}]\n{content}",
                    }
                converted.append(user_msg)
            else:
                converted.append(msg.copy())

        return converted

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream responses from OpenRouter with tool message conversion.

        Args:
            messages: List of messages in OpenAI format.
            tools: Optional list of tools in OpenAI format.
            temperature: Sampling temperature.
            top_p: Nucleus sampling parameter.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters.

        Yields:
            Response chunks in the standard format.
        """
        # Strip tool_calls from assistant messages and convert tool messages to user
        converted_messages = messages
        converted_messages = self._strip_tool_calls_from_assistant_messages(converted_messages)
        converted_messages = self._convert_tool_messages_to_user(converted_messages)

        # Add provider routing parameters if configured
        provider_params = self._build_provider_params()
        if provider_params:
            # OpenRouter requires provider params in extra_body
            extra_body = kwargs.get("extra_body", {})
            extra_body["provider"] = provider_params
            kwargs["extra_body"] = extra_body

        # Call parent stream with converted messages
        if os.environ.get("DEBUG"):
            import rich
            rich.inspect(converted_messages, title="Converted Messages")
        async for chunk in super().stream(
            converted_messages,
            tools=tools,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            **kwargs,
        ):
            yield chunk

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate a complete response from OpenRouter with tool message conversion.

        Args:
            messages: List of messages in OpenAI format.
            tools: Optional list of tools in OpenAI format.
            temperature: Sampling temperature.
            top_p: Nucleus sampling parameter.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters.

        Returns:
            Complete response in the standard format.
        """
        # Strip tool_calls from assistant messages and convert tool messages to user
        converted_messages = messages
        # converted_messages = self._strip_tool_calls_from_assistant_messages(messages)
        converted_messages = self._convert_tool_messages_to_user(converted_messages)

        # Add provider routing parameters if configured
        provider_params = self._build_provider_params()
        if provider_params:
            # OpenRouter requires provider params in extra_body
            extra_body = kwargs.get("extra_body", {})
            extra_body["provider"] = provider_params
            kwargs["extra_body"] = extra_body

        # Call parent generate with converted messages
        return await super().generate(
            converted_messages,
            tools=tools,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            **kwargs,
        )
