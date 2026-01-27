"""Example demonstrating MCP (Model Context Protocol) integration."""

import asyncio
import os

from minicode import Agent, MCPClient
from minicode.llm import OpenAILLM


async def example_direct_mcp_integration() -> None:
    """Example: Agent with direct MCP server configuration (recommended)."""
    print("\n" + "=" * 60)
    print("Example 1: Direct MCP Integration (Recommended)")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Skipping: OPENAI_API_KEY not set")
        return

    # Configure MCP servers directly in Agent constructor
    mcp_servers = [
        {
            "name": "memory",
            "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
        },
    ]

    # Use async context manager for automatic MCP lifecycle management
    async with Agent(
        name="mcp-assistant",
        llm=OpenAILLM(api_key=api_key),
        system_prompt="You are a helpful assistant with memory capabilities via MCP.",
        mcp_servers=mcp_servers,
    ) as agent:
        # List available tools
        print(f"\nDiscovered {len(agent.tool_registry)} tools:")
        for tool_name in agent.tool_registry.list_tools():
            print(f"  - {tool_name}")

        # Use the agent
        print("\n--- Agent Response ---")
        async for chunk in agent.stream("What tools do you have available?"):
            if chunk.get("type") == "content":
                print(chunk.get("content", ""), end="", flush=True)
        print("\n")


async def example_manual_mcp_integration() -> None:
    """Example: Manual MCP client management."""
    print("\n" + "=" * 60)
    print("Example 2: Manual MCP Client Management")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Skipping: OPENAI_API_KEY not set")
        return

    # Create and manage MCP client manually
    mcp_client = MCPClient()

    try:
        # Add MCP server
        await mcp_client.add_server(
            name="memory",
            command=["npx", "-y", "@modelcontextprotocol/server-memory"],
        )

        # Get MCP tools
        mcp_tools = mcp_client.get_tools()
        print(f"\nDiscovered {len(mcp_tools)} MCP tools:")
        for tool in mcp_tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")

        # Create agent with MCP tools
        agent = Agent(
            name="mcp-assistant",
            llm=OpenAILLM(api_key=api_key),
            system_prompt="You are a helpful assistant.",
            tools=mcp_tools,
        )

        # Use the agent
        print("\n--- Agent Response ---")
        async for chunk in agent.stream("Store a note: Remember to buy groceries"):
            if chunk.get("type") == "content":
                print(chunk.get("content", ""), end="", flush=True)
            elif chunk.get("type") == "tool_call":
                tool_call = chunk.get("tool_call", {})
                func = tool_call.get("function", {})
                print(f"\n[Tool Call: {func.get('name')}]")
            elif chunk.get("type") == "tool_result":
                print(f"[Tool Result: {chunk.get('tool_name')}]")
        print("\n")

    finally:
        # Clean up MCP connections
        await mcp_client.disconnect_all()


async def example_multiple_mcp_servers() -> None:
    """Example: Using multiple MCP servers."""
    print("\n" + "=" * 60)
    print("Example 3: Multiple MCP Servers")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Skipping: OPENAI_API_KEY not set")
        return

    # Configure multiple MCP servers
    mcp_servers = [
        {
            "name": "memory-1",
            "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
        },
        {
            "name": "memory-2",
            "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
        },
    ]

    async with Agent(
        name="multi-mcp-assistant",
        llm=OpenAILLM(api_key=api_key),
        system_prompt="You are a helpful assistant with multiple memory systems.",
        mcp_servers=mcp_servers,
    ) as agent:
        print(f"\nTotal tools from all servers: {len(agent.tool_registry)}")
        for tool_name in agent.tool_registry.list_tools():
            print(f"  - {tool_name}")


async def example_http_mcp_server() -> None:
    """Example: HTTP-based MCP server configuration."""
    print("\n" + "=" * 60)
    print("Example 4: HTTP MCP Server (Documentation)")
    print("=" * 60)

    print("""
To connect to an HTTP-based MCP server:

    mcp_servers = [
        {
            "name": "remote-server",
            "url": "http://localhost:8080/mcp",
            "headers": {"Authorization": "Bearer your-token"},
        },
    ]

    async with Agent(
        name="remote-assistant",
        llm=OpenAILLM(api_key=api_key),
        mcp_servers=mcp_servers,
    ) as agent:
        # Use the agent...
        pass
""")


async def main() -> None:
    """Run all MCP examples."""
    print("MCP (Model Context Protocol) Integration Examples")
    print("=" * 60)
    print("\nMCP allows agents to connect to external servers that")
    print("provide additional tools and capabilities.")
    print("\nKey features:")
    print("  - Direct MCP server configuration in Agent constructor")
    print("  - Async context manager for automatic lifecycle management")
    print("  - Support for both stdio and HTTP transports")
    print("  - Multiple MCP servers can be used simultaneously")

    # Run examples
    await example_direct_mcp_integration()
    await example_manual_mcp_integration()
    await example_multiple_mcp_servers()
    await example_http_mcp_server()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("\nFor more information on MCP:")
    print("  https://modelcontextprotocol.io/")


if __name__ == "__main__":
    asyncio.run(main())
