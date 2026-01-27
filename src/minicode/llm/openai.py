"""OpenAI LLM implementation."""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

from minicode.llm.base import BaseLLM
from minicode.utils import retry_with_exponential_backoff


class OpenAILLM(BaseLLM):
    """OpenAI LLM implementation.

    This class provides integration with OpenAI's API.
    Requires the 'openai' package to be installed.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
    ):
        """Initialize OpenAI LLM.

        Args:
            api_key: OpenAI API key (if not provided, will use OPENAI_API_KEY env var)
            model: Model name to use (default: gpt-4)
            base_url: Optional base URL for API (for custom endpoints)
            organization: Optional organization ID
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install it with: pip install minicode[openai]"
            )

        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            organization=organization,
        )

    @retry_with_exponential_backoff(
        max_retries=3,
        initial_wait=2.0,
        max_wait=30.0,
        exceptions=(Exception,),  # Catch all exceptions including InternalServerError
    )
    async def _create_stream(self, params: Dict[str, Any]):
        """Create a stream with retry logic.

        Args:
            params: Parameters for the API call.

        Returns:
            Async stream from OpenAI API.
        """
        return await self.client.chat.completions.create(**params)

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream responses from OpenAI."""
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        if tools:
            params["tools"] = tools

        params.update(kwargs)

        stream = await self._create_stream(params)

        tool_calls_buffer: Dict[int, Dict[str, Any]] = {}

        async for chunk in stream:
            delta = chunk.choices[0].delta

            # Handle content
            if delta.content:
                yield {
                    "type": "content",
                    "content": delta.content,
                }

            # Handle tool calls
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    idx = tool_call.index

                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {
                            "id": tool_call.id or "",
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name or "",
                                "arguments": "",
                            },
                        }

                    if tool_call.function.name:
                        tool_calls_buffer[idx]["function"]["name"] = tool_call.function.name

                    if tool_call.function.arguments:
                        tool_calls_buffer[idx]["function"][
                            "arguments"
                        ] += tool_call.function.arguments

            # Check if done
            if chunk.choices[0].finish_reason:
                # Emit any buffered tool calls
                if tool_calls_buffer:
                    for tool_call in tool_calls_buffer.values():
                        # Parse arguments JSON
                        try:
                            tool_call["function"]["arguments"] = json.loads(
                                tool_call["function"]["arguments"]
                            )
                        except json.JSONDecodeError:
                            # If parsing fails, keep as string
                            pass

                        yield {
                            "type": "tool_call",
                            "tool_call": tool_call,
                        }

                yield {
                    "type": "done",
                    "finish_reason": chunk.choices[0].finish_reason,
                }

    @retry_with_exponential_backoff(
        max_retries=3,
        initial_wait=2.0,
        max_wait=30.0,
        exceptions=(Exception,),
    )
    async def _create_completion(self, params: Dict[str, Any]):
        """Create a completion with retry logic.

        Args:
            params: Parameters for the API call.

        Returns:
            Response from OpenAI API.
        """
        return await self.client.chat.completions.create(**params)

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate a complete response from OpenAI."""
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        if tools:
            params["tools"] = tools

        params.update(kwargs)

        response = await self._create_completion(params)
        choice = response.choices[0]
        message = choice.message

        result: Dict[str, Any] = {
            "content": message.content or "",
            "finish_reason": choice.finish_reason,
        }

        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    },
                }
                for tc in message.tool_calls
            ]

        return result

    async def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken if available."""
        try:
            import tiktoken

            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except ImportError:
            # Fall back to default estimation
            return await super().count_tokens(text)
