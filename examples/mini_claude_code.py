#!/usr/bin/env python3
"""Mini Claude Code - A full-featured coding assistant in ~20 lines.

This showcase demonstrates how minicode SDK makes it trivial to build
a Claude Code equivalent with all essential features.

Usage:
    export ANTHROPIC_API_KEY=your_key_here
    python mini_claude_code.py
"""

import asyncio
import os
from minicode import Agent
from minicode.llm import AnthropicLLM
from minicode.tools.builtin import (
    ReadTool, WriteTool, EditTool, GlobTool, GrepTool,
    BashTool, WebFetchTool, WebSearchTool, AskUserQuestionTool,
    TaskTool, ThinkTool, SkillTool
)

async def main():
    """Run mini Claude Code."""
    # Create agent with all essential tools (1 line)
    agent = Agent(
        name="MiniClaudeCode",
        llm=AnthropicLLM(api_key=os.getenv("ANTHROPIC_API_KEY")),
        tools=[
            ReadTool(), WriteTool(), EditTool(), GlobTool(), GrepTool(),  # File ops
            BashTool(), WebFetchTool(), WebSearchTool(),                   # Execution & Web
            AskUserQuestionTool(), TaskTool(), ThinkTool(), SkillTool()   # Advanced
        ],
        prompt="""You are an expert coding assistant with access to powerful tools.

Key capabilities:
- Read/write/edit files with precision
- Search codebases (glob patterns, regex grep)
- Execute commands and scripts
- Fetch web content and search online
- Ask clarifying questions when needed
- Delegate complex tasks to sub-agents
- Record your reasoning process
- Access specialized skills

Always think step-by-step and use tools effectively."""
    )

    # Interactive REPL (18 lines total including imports and this function)
    print("🤖 Mini Claude Code - Type your request (Ctrl+C to exit)")
    print("=" * 70)

    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            if not user_input:
                continue

            print(f"\n🤔 {agent.name}:")
            async for chunk in agent.stream(user_input):
                if chunk.get("type") == "content":
                    print(chunk.get("content", ""), end="", flush=True)
            print()  # Newline after response

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
