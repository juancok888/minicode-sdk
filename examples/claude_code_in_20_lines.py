#!/usr/bin/env python3
"""Claude Code in 20 Lines

A production-ready coding assistant with file ops, shell execution,
web access, sub-agents, and more - all in just 20 lines of code.

Setup: export OPENROUTER_API_KEY=your_key
Usage: python claude_code_in_20_lines.py
"""
import asyncio, os
from minicode import Agent
from minicode.llm import OpenRouterLLM
from minicode.tools.builtin import *
async def main():
    llm = OpenRouterLLM(api_key=os.getenv("OPENROUTER_API_KEY"), model="anthropic/claude-haiku-4.5", provider="google-vertex")  # Use Anthropic provider directly
    tools = [ReadTool(), WriteTool(), EditTool(), GlobTool(), GrepTool(), BashTool(), WebFetchTool(), WebSearchTool(), TaskTool(), ThinkTool(), SkillTool(), AskUserQuestionTool()]
    agent = Agent("ClaudeCode", llm, "You are a helpful coding assistant.", tools)
    while True:
        if msg := input("\n💬 User: ").strip():
            print(f"\n🤔 Agent:")
            async for chunk in agent.stream(msg):
                chunk_type = chunk.get("type")
                if chunk_type == "content":
                    print(chunk.get("content", ""), end="", flush=True)
                elif chunk_type == "tool_call":
                    func = chunk.get("tool_call", {}).get("function", {})
                    print(f"\n🔧 [TOOL] {func.get('name')} | 参数: {func.get('arguments')}")
                elif chunk_type == "tool_result":
                    print(f"📋 [RESULT] {chunk.get('tool_name')}: {chunk.get('result')}")
            print()
asyncio.run(main())
