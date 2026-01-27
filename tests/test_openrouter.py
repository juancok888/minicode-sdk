#!/usr/bin/env python3
"""Test OpenRouterLLM with tool calls."""
import asyncio
import os
from minicode import Agent
from minicode.llm import OpenRouterLLM
from minicode.tools.builtin import ReadTool, BashTool

async def main():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set")
        return

    print("Testing OpenRouterLLM with tool message conversion...")
    print("=" * 60)

    llm = OpenRouterLLM(
        api_key=api_key,
        model="anthropic/claude-3.5-haiku"
    )

    agent = Agent(
        "TestAgent",
        llm,
        "You are a helpful assistant.",
        [ReadTool(), BashTool()]
    )

    # Test: File read with tool call
    print("\n🧪 Test: Read a file (with tool call)")
    print("-" * 60)

    try:
        async for chunk in agent.stream("Read the file examples/claude_code_in_20_lines.py and tell me what it does."):
            chunk_type = chunk.get("type")
            if chunk_type == "content":
                print(chunk.get("content", ""), end="", flush=True)
            elif chunk_type == "tool_call":
                tool_name = chunk.get("tool_call", {}).get("function", {}).get("name", "")
                print(f"\n  🔧 Calling tool: {tool_name}", flush=True)
            elif chunk_type == "tool_result":
                print(f" ✓", flush=True)

        print("\n\n✅ Test PASSED!")

    except Exception as e:
        print(f"\n\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
