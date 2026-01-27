#!/usr/bin/env python3
"""OpenRouter Provider Selection Examples.

This example demonstrates how to specify providers when using OpenRouter.

Available providers:
- anthropic: Direct Anthropic API
- amazon-bedrock: AWS Bedrock
- google-vertex: Google Vertex AI

Note: Provider parameters are passed via OpenAI's extra_body parameter
to the OpenRouter API. This is handled automatically by OpenRouterLLM.
"""
import asyncio
import os

from minicode import Agent
from minicode.llm import OpenRouterLLM
from minicode.tools.builtin import ReadTool, WriteTool


async def example_single_provider():
    """Example: Use single provider only (no fallback)."""
    print("=" * 60)
    print("Example 1: Single Provider (Anthropic only)")
    print("=" * 60)

    llm = OpenRouterLLM(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="anthropic/claude-3.5-haiku",
        provider="anthropic",  # Use Anthropic provider only
        allow_fallbacks=False,  # Don't fall back to other providers
    )

    agent = Agent("Assistant", llm, "You are a helpful assistant.", [ReadTool()])

    response = await agent.generate("What is 2+2?")
    print(f"Response: {response}\n")


async def example_multiple_providers():
    """Example: Use multiple providers with priority order."""
    print("=" * 60)
    print("Example 2: Multiple Providers with Priority")
    print("=" * 60)

    llm = OpenRouterLLM(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="anthropic/claude-3.5-haiku",
        provider=["anthropic", "amazon-bedrock", "google-vertex"],  # Priority order
        allow_fallbacks=True,  # Allow fallback if first provider fails
    )

    agent = Agent("Assistant", llm, "You are a helpful assistant.", [ReadTool()])

    response = await agent.generate("What is 3+3?")
    print(f"Response: {response}\n")


async def example_auto_routing():
    """Example: Let OpenRouter choose the best provider automatically."""
    print("=" * 60)
    print("Example 3: Auto Routing (OpenRouter chooses)")
    print("=" * 60)

    llm = OpenRouterLLM(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="anthropic/claude-3.5-haiku",
        provider=None,  # Let OpenRouter choose automatically
    )

    agent = Agent("Assistant", llm, "You are a helpful assistant.", [ReadTool()])

    response = await agent.generate("What is 5+5?")
    print(f"Response: {response}\n")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("OpenRouter Provider Selection Examples")
    print("=" * 60 + "\n")

    # Example 1: Single provider
    await example_single_provider()

    # Example 2: Multiple providers with priority
    await example_multiple_providers()

    # Example 3: Auto routing
    await example_auto_routing()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
