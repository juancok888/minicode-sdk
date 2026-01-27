"""Base LLM abstraction for minicode SDK."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional


class BaseLLM(ABC):
    """Abstract base class for LLM implementations.

    This class defines the interface that all LLM implementations must follow.
    Users can extend this class to integrate their own LLM providers.
    """

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream responses from the LLM.

        Args:
            messages: List of messages in the conversation
            tools: Optional list of tools available for function calling
            temperature: Sampling temperature (0.0 to 2.0)
            top_p: Nucleus sampling parameter
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Yields:
            Dictionary chunks representing the streaming response.
            Each chunk should contain:
            - 'type': 'content' | 'tool_call' | 'done'
            - 'content': str (for content chunks)
            - 'tool_call': dict (for tool call chunks)
            - Other provider-specific fields

        Example:
            async for chunk in llm.stream(messages):
                if chunk['type'] == 'content':
                    print(chunk['content'])
                elif chunk['type'] == 'tool_call':
                    tool_name = chunk['tool_call']['name']
                    tool_args = chunk['tool_call']['arguments']
        """
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate a complete response from the LLM (non-streaming).

        Args:
            messages: List of messages in the conversation
            tools: Optional list of tools available for function calling
            temperature: Sampling temperature (0.0 to 2.0)
            top_p: Nucleus sampling parameter
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            A dictionary containing the complete response with:
            - 'content': str (the generated text)
            - 'tool_calls': list (if the model wants to call tools)
            - 'finish_reason': str ('stop', 'length', 'tool_calls', etc.)
            - Other provider-specific fields

        Example:
            response = await llm.generate(messages)
            print(response['content'])
        """
        pass

    async def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text.

        This is an optional method that can be overridden by implementations
        that support token counting.

        Args:
            text: The text to count tokens for

        Returns:
            The number of tokens (approximate if not supported)
        """
        # Default implementation: rough estimate
        return len(text) // 4
