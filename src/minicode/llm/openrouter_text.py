"""Text-based tool calling for OpenRouter LLM.

This implementation uses XML-style tags for tool calling instead of function calling,
making it compatible with models that don't support native function calling.
"""

import json
import re
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from minicode.llm.openai import OpenAILLM


class TextBasedOpenRouterLLM(OpenAILLM):
    """OpenRouter LLM with text-based tool calling.

    Uses XML tags for tool calling instead of function calling API.
    This makes it compatible with more models on OpenRouter.

    Tool calling format:
        <tool_call>
        <tool_name>read_file</tool_name>
        <parameters>
        {
            "file_path": "/path/to/file"
        }
        </parameters>
        </tool_call>

    Tool result format (injected as user message):
        <tool_result>
        <tool_name>read_file</tool_name>
        <result>
        {
            "success": true,
            "data": "file contents..."
        }
        </result>
        </tool_result>
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "anthropic/claude-3.5-haiku",
        organization: Optional[str] = None,
        provider: Optional[Union[str, List[str]]] = None,
        allow_fallbacks: bool = True,
    ):
        """Initialize TextBasedOpenRouterLLM.

        Args:
            api_key: OpenRouter API key (if not provided, will use OPENROUTER_API_KEY env var)
            model: Model name to use (default: anthropic/claude-3.5-haiku)
            organization: Optional organization ID
            provider: Provider to use. Can be:
                - Single provider string: "anthropic", "amazon-bedrock", "google-vertex"
                - List of providers in priority order: ["anthropic", "amazon-bedrock"]
                - None (default): Let OpenRouter choose automatically
            allow_fallbacks: Whether to allow fallback to other providers (default: True)
        """
        super().__init__(
            api_key=api_key,
            model=model,
            base_url="https://openrouter.ai/api/v1",
            organization=organization,
        )

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

        if isinstance(self.provider, str):
            provider_config["only"] = [self.provider]
        else:
            provider_config["order"] = self.provider

        if not self.allow_fallbacks:
            provider_config["allow_fallbacks"] = False

        return provider_config

    def _build_tools_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """Build a text description of available tools for the system prompt.

        Args:
            tools: List of tools in OpenAI format.

        Returns:
            Formatted text description of tools.
        """
        if not tools:
            return ""

        tools_text = "\n\n# Available Tools\n\n"
        tools_text += "You have access to the following tools. To use a tool, respond with XML tags in this format:\n\n"
        tools_text += "<tool_call>\n"
        tools_text += "<tool_name>tool_name_here</tool_name>\n"
        tools_text += "<parameters>\n"
        tools_text += "{\n"
        tools_text += '  "param1": "value1",\n'
        tools_text += '  "param2": "value2"\n'
        tools_text += "}\n"
        tools_text += "</parameters>\n"
        tools_text += "</tool_call>\n\n"
        tools_text += "## Tool Definitions:\n\n"

        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "")
            description = func.get("description", "")
            parameters = func.get("parameters", {})

            tools_text += f"### {name}\n\n"
            tools_text += f"{description}\n\n"

            if parameters:
                props = parameters.get("properties", {})
                required = parameters.get("required", [])

                tools_text += "**Parameters:**\n\n"
                for prop_name, prop_info in props.items():
                    prop_type = prop_info.get("type", "string")
                    prop_desc = prop_info.get("description", "")
                    required_mark = " (required)" if prop_name in required else " (optional)"
                    tools_text += f"- `{prop_name}` ({prop_type}){required_mark}: {prop_desc}\n"

            tools_text += "\n"

        return tools_text

    def _extract_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Extract tool calls from text using XML tags.

        Args:
            text: The text content to parse.

        Returns:
            List of tool call dictionaries.
        """
        tool_calls = []

        # Pattern to match <tool_call>...</tool_call> blocks
        pattern = r"<tool_call>(.*?)</tool_call>"
        matches = re.findall(pattern, text, re.DOTALL)

        for match in matches:
            # Extract tool name
            name_match = re.search(r"<tool_name>(.*?)</tool_name>", match, re.DOTALL)
            if not name_match:
                continue

            tool_name = name_match.group(1).strip()

            # Extract parameters
            params_match = re.search(r"<parameters>(.*?)</parameters>", match, re.DOTALL)
            params = {}
            if params_match:
                params_text = params_match.group(1).strip()
                try:
                    params = json.loads(params_text)
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to be lenient
                    params = {"raw": params_text}

            tool_calls.append({
                "id": f"call_{len(tool_calls)}",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": params,
                }
            })

        return tool_calls

    def _inject_tools_into_system(
        self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Inject tool descriptions into system message.

        Args:
            messages: Original messages.
            tools: Tool definitions.

        Returns:
            Modified messages with tools in system prompt.
        """
        if not tools:
            return messages

        tools_prompt = self._build_tools_prompt(tools)

        # Find or create system message
        modified = messages.copy()
        system_idx = None

        for i, msg in enumerate(modified):
            if msg.get("role") == "system":
                system_idx = i
                break

        if system_idx is not None:
            # Append to existing system message
            modified[system_idx] = modified[system_idx].copy()
            modified[system_idx]["content"] = modified[system_idx]["content"] + tools_prompt
        else:
            # Create new system message
            modified.insert(0, {
                "role": "system",
                "content": tools_prompt,
            })

        return modified

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream responses with text-based tool calling.

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
        # Inject tools into system prompt
        messages_with_tools = self._inject_tools_into_system(messages, tools)

        # Add provider routing if configured
        provider_params = self._build_provider_params()
        if provider_params:
            extra_body = kwargs.get("extra_body", {})
            extra_body["provider"] = provider_params
            kwargs["extra_body"] = extra_body

        # Stream without tools parameter (using text-based approach)
        content_buffer = []

        async for chunk in super().stream(
            messages_with_tools,
            tools=None,  # Don't use function calling
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            **kwargs,
        ):
            chunk_type = chunk.get("type")

            if chunk_type == "content":
                content = chunk.get("content", "")
                content_buffer.append(content)
                yield chunk

            elif chunk_type == "done":
                # Parse complete content for tool calls
                full_content = "".join(content_buffer)
                tool_calls = self._extract_tool_calls(full_content)

                if tool_calls:
                    # Emit tool calls
                    for tool_call in tool_calls:
                        yield {
                            "type": "tool_call",
                            "tool_call": tool_call,
                        }

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
        """Generate a complete response with text-based tool calling.

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
        # Inject tools into system prompt
        messages_with_tools = self._inject_tools_into_system(messages, tools)

        # Add provider routing if configured
        provider_params = self._build_provider_params()
        if provider_params:
            extra_body = kwargs.get("extra_body", {})
            extra_body["provider"] = provider_params
            kwargs["extra_body"] = extra_body

        # Generate without tools parameter
        response = await super().generate(
            messages_with_tools,
            tools=None,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            **kwargs,
        )

        # Parse content for tool calls
        content = response.get("content", "")
        tool_calls = self._extract_tool_calls(content)

        if tool_calls:
            response["tool_calls"] = tool_calls

        return response
