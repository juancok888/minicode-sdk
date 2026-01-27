"""Basic agent example demonstrating core minicode functionality."""

import asyncio
import os

from minicode import Agent
from minicode.llm import OpenAILLM
from minicode.tools import ReadTool, WriteTool


async def main() -> None:
    """Run a basic agent example."""
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    # Create an agent with OpenAI LLM and file tools
    agent = Agent(
        name="assistant",
        llm=OpenAILLM(api_key=api_key, model="gpt-4"),
        tools=[ReadTool(), WriteTool()],
        prompt="You are a helpful coding assistant. You can read and write files.",
        temperature=0.7,
    )

    print("Agent initialized! Type 'quit' to exit.\n")

    # Interactive loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            if not user_input:
                continue

            # Stream the agent's response
            print("Agent: ", end="", flush=True)

            async for chunk in agent.stream(user_input):
                chunk_type = chunk.get("type")

                if chunk_type == "content":
                    # Print content as it streams
                    print(chunk.get("content", ""), end="", flush=True)

                elif chunk_type == "tool_call":
                    # Show tool call
                    tool_call = chunk.get("tool_call", {})
                    function = tool_call.get("function", {})
                    print(
                        f"\n[Calling tool: {function.get('name')}]",
                        flush=True,
                    )

                elif chunk_type == "tool_result":
                    # Show tool result
                    tool_name = chunk.get("tool_name", "")
                    result = chunk.get("result", {})
                    success = result.get("success", False)
                    status = "✓" if success else "✗"
                    print(f"[Tool {tool_name} {status}]", flush=True)

                elif chunk_type == "done":
                    # Response complete
                    print("\n")
                    break

                elif chunk_type == "error":
                    # Handle errors
                    print(f"\n[Error: {chunk.get('error')}]\n")
                    break

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
