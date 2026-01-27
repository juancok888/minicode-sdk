"""Example demonstrating how to create a custom LLM implementation."""

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional

from minicode import Agent
from minicode.llm import BaseLLM
from minicode.tools import ReadTool


class MockLLM(BaseLLM):
    """A mock LLM for demonstration purposes.

    This simple implementation shows how to create a custom LLM
    that integrates with minicode's agent system.
    """

    def __init__(self, response_template: str = "I received: {message}"):
        """Initialize the mock LLM.

        Args:
            response_template: Template for generating responses
        """
        self.response_template = response_template

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream a mock response."""
        # Get the last user message
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break

        # Generate response
        response = self.response_template.format(message=last_message)

        # Simulate streaming by yielding words
        words = response.split()
        for word in words:
            await asyncio.sleep(0.1)  # Simulate delay
            yield {
                "type": "content",
                "content": word + " ",
            }

        # Signal completion
        yield {
            "type": "done",
            "finish_reason": "stop",
        }

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate a complete mock response."""
        # Get the last user message
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break

        # Generate response
        response = self.response_template.format(message=last_message)

        return {
            "content": response,
            "finish_reason": "stop",
        }


async def main() -> None:
    """Run the custom LLM example."""
    print("Custom LLM Example")
    print("=" * 50)

    # Create an agent with our custom mock LLM
    agent = Agent(
        name="mock-assistant",
        llm=MockLLM(
            response_template="Thanks for your message: '{message}'. "
            "I'm a mock LLM demonstrating custom implementations!"
        ),
        tools=[ReadTool()],
        prompt="You are a demonstration agent using a custom LLM.",
    )

    # Test the agent
    print("\nSending message to agent...\n")

    async for chunk in agent.stream("Hello, custom LLM!"):
        if chunk.get("type") == "content":
            print(chunk.get("content", ""), end="", flush=True)

    print("\n\nExample complete!")
    print("\nTo create your own LLM:")
    print("1. Extend the BaseLLM class")
    print("2. Implement the stream() and generate() methods")
    print("3. Handle tool calls if needed")
    print("4. Return responses in the expected format")


if __name__ == "__main__":
    asyncio.run(main())
