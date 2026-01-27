"""Comprehensive example showing all minicode features working together."""

import asyncio
import os
from pathlib import Path

from minicode import Agent
from minicode.llm import BaseLLM
from minicode.skills import SkillLoader
from minicode.tools import ReadTool, WriteTool


class DemoLLM(BaseLLM):
    """Demo LLM that simulates intelligent responses."""

    async def stream(self, messages, tools=None, **kwargs):
        """Stream intelligent-looking responses."""
        # Get last user message
        last_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_msg = msg.get("content", "")
                break

        # Check if we just got tool results
        has_tool_results = any(msg.get("role") == "tool" for msg in messages[-3:])

        # Simulate intelligent response based on context
        if "read" in last_msg.lower() and not has_tool_results:
            # Simulate tool call for reading
            yield {
                "type": "tool_call",
                "tool_call": {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": {"path": "/tmp/demo_file.txt"},
                    },
                },
            }
            yield {"type": "done", "finish_reason": "tool_calls"}
        elif has_tool_results:
            # After tool execution, provide a summary
            response = "I've read the file successfully. "
            for word in response.split():
                await asyncio.sleep(0.05)
                yield {"type": "content", "content": word + " "}
            yield {"type": "done", "finish_reason": "stop"}
        else:
            # Regular response
            response = (
                f"I understand you said: '{last_msg}'. "
                f"I have access to {len(tools) if tools else 0} tools. "
            )
            for word in response.split():
                await asyncio.sleep(0.05)
                yield {"type": "content", "content": word + " "}
            yield {"type": "done", "finish_reason": "stop"}

    async def generate(self, messages, **kwargs):
        """Generate complete response."""
        last_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_msg = msg.get("content", "")
                break
        return {
            "content": f"Response to: {last_msg}",
            "finish_reason": "stop",
        }


async def demo_basic_agent():
    """Demo 1: Basic agent with tools."""
    print("\n" + "=" * 70)
    print("Demo 1: Basic Agent with Tools")
    print("=" * 70)

    agent = Agent(
        name="demo-agent",
        llm=DemoLLM(),
        tools=[ReadTool(), WriteTool()],
        prompt="You are a helpful demo agent.",
    )

    print(f"\nAgent '{agent.name}' initialized with {len(agent.tool_registry)} tools")
    print(f"Available tools: {', '.join(agent.tool_registry.list_tools())}")

    # Test conversation
    print("\nUser: Hello, what can you do?")
    print("Agent: ", end="", flush=True)

    async for chunk in agent.stream("Hello, what can you do?"):
        if chunk.get("type") == "content":
            print(chunk.get("content", ""), end="", flush=True)
        elif chunk.get("type") == "done":
            print()
            break


async def demo_file_operations():
    """Demo 2: File operations with tools."""
    print("\n" + "=" * 70)
    print("Demo 2: File Operations")
    print("=" * 70)

    agent = Agent(
        name="file-agent",
        llm=DemoLLM(),
        tools=[ReadTool(), WriteTool()],
        prompt="You are a file management assistant.",
    )

    # Create a test file first
    demo_file = Path("/tmp/demo_file.txt")
    demo_file.write_text("Hello from minicode!\nThis is a demo file.")

    print(f"\nCreated demo file: {demo_file}")
    print("\nUser: Please read the demo file")
    print("Agent: ", end="", flush=True)

    async for chunk in agent.stream(f"Read the file at {demo_file}"):
        chunk_type = chunk.get("type")
        if chunk_type == "content":
            print(chunk.get("content", ""), end="", flush=True)
        elif chunk_type == "tool_call":
            print("\n[Calling tool...]", flush=True)
        elif chunk_type == "tool_result":
            result = chunk.get("result", {})
            if result.get("success"):
                print(f"[Tool succeeded: {result.get('path')}]")
                print(f"File content: {result.get('data')}")
        elif chunk_type == "done":
            print()
            break


async def demo_skills():
    """Demo 3: Skills system."""
    print("\n" + "=" * 70)
    print("Demo 3: Skills System")
    print("=" * 70)

    # Create a temporary skill directory
    skill_dir = Path("/tmp/demo_skills")
    skill_dir.mkdir(exist_ok=True)

    # Create a sample skill
    skill_file = skill_dir / "summarize.md"
    skill_file.write_text(
        """# Summarize Text

This skill summarizes text content.

## Parameters
- text: The text to summarize
- max_length: Maximum length of summary

## Content
Please provide a concise summary of the following text (max {max_length} words):

{text}

Summary:
"""
    )

    # Load skills
    loader = SkillLoader(skill_dirs=[str(skill_dir)])
    skills = loader.load_all_skills()

    print(f"\nLoaded {len(skills)} skill(s) from {skill_dir}")

    if skills:
        for skill in skills:
            print(f"  - {skill.name}: {skill.description}")

        # Create agent with skills
        agent = Agent(
            name="skilled-agent",
            llm=DemoLLM(),
            tools=skills,
            prompt="You are an agent with specialized skills.",
        )

        print(f"\nAgent has access to {len(agent.tool_registry)} skill(s)")


async def demo_agent_modes():
    """Demo 4: Different agent modes."""
    print("\n" + "=" * 70)
    print("Demo 4: Agent Modes")
    print("=" * 70)

    modes = ["primary", "subagent", "all"]

    for mode in modes:
        agent = Agent(
            name=f"{mode}-agent",
            llm=DemoLLM(),
            tools=[ReadTool()],
            prompt=f"You are a {mode} agent.",
            mode=mode,
        )
        print(f"\n{mode.upper()} mode agent created: {agent.name}")
        print(f"  Mode: {agent.mode}")
        print(f"  Temperature: {agent.temperature}")
        print(f"  Tools: {len(agent.tool_registry)}")


async def demo_session_management():
    """Demo 5: Session management."""
    print("\n" + "=" * 70)
    print("Demo 5: Session Management")
    print("=" * 70)

    agent = Agent(name="session-agent", llm=DemoLLM(), prompt="You are a demo agent.")

    # First conversation
    print(f"\nInitial session ID: {agent.session_id}")
    await agent.generate("Hello")
    print(f"Messages in session: {len(agent.messages)}")

    # Add more messages
    await agent.generate("How are you?")
    print(f"Messages after second interaction: {len(agent.messages)}")

    # Reset session
    agent.reset_session()
    print(f"\nAfter reset:")
    print(f"  New session ID: {agent.session_id}")
    print(f"  Messages in session: {len(agent.messages)}")


async def demo_custom_prompt():
    """Demo 6: Custom prompts."""
    print("\n" + "=" * 70)
    print("Demo 6: Custom System Prompts")
    print("=" * 70)

    custom_prompts = [
        "You are a helpful coding assistant specializing in Python.",
        "You are a creative writing assistant.",
        "You are a data analysis expert.",
    ]

    for prompt in custom_prompts:
        agent = Agent(name="custom-agent", llm=DemoLLM(), prompt=prompt, temperature=0.8)
        print(f"\nAgent with prompt: {prompt[:50]}...")
        print(f"  Temperature: {agent.temperature}")


async def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("MINICODE COMPREHENSIVE DEMO")
    print("=" * 70)
    print("\nThis demo showcases all major features of the minicode SDK:")
    print("  1. Basic agent with tools")
    print("  2. File operations")
    print("  3. Skills system")
    print("  4. Agent modes")
    print("  5. Session management")
    print("  6. Custom prompts")

    await demo_basic_agent()
    await demo_file_operations()
    await demo_skills()
    await demo_agent_modes()
    await demo_session_management()
    await demo_custom_prompt()

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nKey takeaways:")
    print("  ✓ Agents combine LLMs, tools, and session management")
    print("  ✓ Tools can be built-in, custom, or from MCP servers")
    print("  ✓ Skills provide reusable capabilities from Markdown")
    print("  ✓ Different agent modes support various use cases")
    print("  ✓ Sessions can be managed and reset as needed")
    print("  ✓ Everything is async-first and type-safe")
    print(
        "\nFor more examples, see the examples/ directory or visit:\n"
        "https://github.com/WalterSumbon/minicode-sdk"
    )


if __name__ == "__main__":
    asyncio.run(main())
