"""Example: Using WebSearch and WebFetch tools.

This example demonstrates how to use the web tools to search for information
and fetch web pages.
"""

import asyncio

from minicode.session.message import ToolContext
from minicode.tools.builtin import WebFetchTool, WebSearchTool


async def search_example():
    """Example: Search the web with Exa."""
    print("=" * 80)
    print("Example 1: Web Search with Exa")
    print("=" * 80)

    context = ToolContext(agent_name="example", session_id="demo-session")
    websearch = WebSearchTool(default_backend="exa")

    # Search for Python tutorials
    result = await websearch.execute(
        {
            "query": "Python async programming tutorials 2025",
            "num_results": 3,
            "type": "auto",  # Options: auto, fast, deep
        },
        context,
    )

    if result["success"]:
        print(f"\n✓ Search successful!")
        print(f"Backend: {result['backend']}")
        print(f"Query: {result['query']}")
        print(f"\nResults:\n{result['content'][:500]}...\n")
    else:
        print(f"\n✗ Search failed: {result['error']}")


async def fetch_example():
    """Example: Fetch and convert web pages."""
    print("=" * 80)
    print("Example 2: Fetch Web Page as Markdown")
    print("=" * 80)

    context = ToolContext(agent_name="example", session_id="demo-session")
    webfetch = WebFetchTool()

    # Fetch example.com as markdown
    result = await webfetch.execute(
        {
            "url": "https://example.com",
            "format": "markdown",
            "timeout": 30,
        },
        context,
    )

    if result["success"]:
        print(f"\n✓ Fetch successful!")
        print(f"URL: {result['url']}")
        print(f"Content Type: {result['content_type']}")
        print(f"\nMarkdown Content:\n{result['content'][:400]}...\n")
    else:
        print(f"\n✗ Fetch failed: {result['error']}")


async def fetch_formats_example():
    """Example: Different output formats."""
    print("=" * 80)
    print("Example 3: Different Output Formats")
    print("=" * 80)

    context = ToolContext(agent_name="example", session_id="demo-session")
    webfetch = WebFetchTool()

    formats = ["markdown", "text", "html"]

    for format_type in formats:
        print(f"\n--- Format: {format_type} ---")

        result = await webfetch.execute(
            {
                "url": "https://example.com",
                "format": format_type,
            },
            context,
        )

        if result["success"]:
            content_preview = result["content"][:200].replace("\n", " ")
            print(f"✓ Content preview: {content_preview}...")
        else:
            print(f"✗ Failed: {result['error']}")


async def advanced_search_example():
    """Example: Advanced search with Exa options."""
    print("=" * 80)
    print("Example 4: Advanced Exa Search Options")
    print("=" * 80)

    context = ToolContext(agent_name="example", session_id="demo-session")
    websearch = WebSearchTool(default_backend="exa")

    # Deep search with live crawling
    result = await websearch.execute(
        {
            "query": "latest AI developments 2025",
            "num_results": 5,
            "type": "deep",  # More comprehensive search
            "livecrawl": "preferred",  # Prioritize fresh content
        },
        context,
    )

    if result["success"]:
        print(f"\n✓ Deep search successful!")
        print(f"Found comprehensive results with live crawling")
        print(f"\nResults preview:\n{result['content'][:400]}...\n")
    else:
        print(f"\n✗ Search failed: {result['error']}")


async def search_and_fetch_workflow():
    """Example: Complete workflow - search then fetch."""
    print("=" * 80)
    print("Example 5: Search and Fetch Workflow")
    print("=" * 80)

    context = ToolContext(agent_name="example", session_id="demo-session")

    # Step 1: Search
    print("\n[Step 1] Searching for Python documentation...")
    websearch = WebSearchTool(default_backend="exa")

    search_result = await websearch.execute(
        {
            "query": "Python official documentation",
            "num_results": 1,
        },
        context,
    )

    if not search_result["success"]:
        print(f"✗ Search failed: {search_result['error']}")
        return

    print("✓ Search successful!")

    # Step 2: Fetch the official Python site
    print("\n[Step 2] Fetching Python.org...")
    webfetch = WebFetchTool()

    fetch_result = await webfetch.execute(
        {
            "url": "https://www.python.org",
            "format": "markdown",
            "timeout": 30,
        },
        context,
    )

    if fetch_result["success"]:
        print("✓ Fetch successful!")
        print(f"\nPage content preview:\n{fetch_result['content'][:300]}...\n")
    else:
        print(f"✗ Fetch failed: {fetch_result['error']}")


async def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Web Tools Examples" + " " * 40 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    # Run examples
    await search_example()
    await asyncio.sleep(1)  # Rate limiting

    await fetch_example()
    await asyncio.sleep(1)

    await fetch_formats_example()
    await asyncio.sleep(1)

    await advanced_search_example()
    await asyncio.sleep(1)

    await search_and_fetch_workflow()

    print("\n")
    print("=" * 80)
    print("All examples completed!")
    print("=" * 80)
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
