"""Integration tests for web tools with real API calls.

These tests make actual network requests and should be run manually or in CI
with appropriate rate limiting.
"""

import pytest

from minicode.session.message import ToolContext
from minicode.tools.builtin import WebFetchTool, WebSearchTool


@pytest.fixture
def tool_context():
    """Create a tool context for testing."""
    return ToolContext(agent_name="test", session_id="test-session")


# Mark as integration test that requires network
pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.slow
async def test_websearch_real_query(tool_context):
    """Test WebSearch with a real query to Exa API.

    This test makes an actual API call to Exa and should be run manually
    or with appropriate rate limiting in CI.
    """
    tool = WebSearchTool(default_backend="exa")

    result = await tool.execute(
        {
            "query": "Python programming tutorials 2025",
            "num_results": 3,
            "type": "auto",
        },
        tool_context,
    )

    # Verify the search succeeded
    assert result["success"] is True, f"Search failed: {result.get('error')}"
    assert "content" in result
    assert result["backend"] == "exa"
    assert result["query"] == "Python programming tutorials 2025"

    # Content should contain search results
    assert len(result["content"]) > 0
    print(f"\nSearch results preview:\n{result['content'][:500]}...")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_websearch_with_options(tool_context):
    """Test WebSearch with advanced Exa options."""
    tool = WebSearchTool(default_backend="exa")

    result = await tool.execute(
        {
            "query": "artificial intelligence latest news",
            "num_results": 5,
            "type": "fast",
            "livecrawl": "fallback",
        },
        tool_context,
    )

    assert result["success"] is True
    assert result["backend"] == "exa"
    assert "content" in result


@pytest.mark.asyncio
@pytest.mark.slow
async def test_webfetch_real_page(tool_context):
    """Test WebFetch with a real web page.

    This test fetches an actual web page and converts it to markdown.
    """
    tool = WebFetchTool()

    # Fetch example.com (a simple, stable test page)
    result = await tool.execute(
        {
            "url": "https://example.com",
            "format": "markdown",
            "timeout": 30,
        },
        tool_context,
    )

    # Verify the fetch succeeded
    assert result["success"] is True, f"Fetch failed: {result.get('error')}"
    assert "content" in result
    assert result["url"] == "https://example.com"

    # Content should contain expected text from example.com
    assert "Example Domain" in result["content"]
    print(f"\nFetched content preview:\n{result['content'][:300]}...")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_webfetch_html_format(tool_context):
    """Test WebFetch with HTML format."""
    tool = WebFetchTool()

    result = await tool.execute(
        {
            "url": "https://example.com",
            "format": "html",
        },
        tool_context,
    )

    assert result["success"] is True
    assert "<html" in result["content"].lower()
    assert "<body" in result["content"].lower()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_webfetch_text_format(tool_context):
    """Test WebFetch with plain text format."""
    tool = WebFetchTool()

    result = await tool.execute(
        {
            "url": "https://example.com",
            "format": "text",
        },
        tool_context,
    )

    assert result["success"] is True
    # Text format should not contain HTML tags
    assert "<html" not in result["content"].lower()
    assert "<body" not in result["content"].lower()
    assert "Example Domain" in result["content"]


@pytest.mark.asyncio
@pytest.mark.slow
async def test_search_and_fetch_workflow(tool_context):
    """Test a complete workflow: search then fetch a result.

    This demonstrates a real-world use case where you search for something
    and then fetch one of the results.
    """
    # Step 1: Search for Python documentation
    websearch = WebSearchTool(default_backend="exa")
    search_result = await websearch.execute(
        {
            "query": "Python official documentation",
            "num_results": 1,
        },
        tool_context,
    )

    assert search_result["success"] is True
    print(f"\nSearch found results")

    # Step 2: Fetch example.com as a proxy for fetching search results
    # (In a real scenario, you'd extract URLs from search results)
    webfetch = WebFetchTool()
    fetch_result = await webfetch.execute(
        {
            "url": "https://www.python.org",
            "format": "markdown",
            "timeout": 30,
        },
        tool_context,
    )

    assert fetch_result["success"] is True
    assert "python" in fetch_result["content"].lower()
    print(f"\nFetched page successfully")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_websearch_anime_query(tool_context):
    """Test WebSearch with an anime-related query.

    This test demonstrates searching for specific content (anime news)
    which was the original use case.
    """
    tool = WebSearchTool(default_backend="exa")

    result = await tool.execute(
        {
            "query": "魔法少女まどか☆マギカ ワルプルギスの廻天 latest news 2025",
            "num_results": 5,
            "type": "auto",
        },
        tool_context,
    )

    assert result["success"] is True
    assert result["backend"] == "exa"
    assert len(result["content"]) > 0

    # Print results for manual verification
    print(f"\n=== Anime Search Results ===")
    print(result["content"][:1000])
    print("...")


@pytest.mark.asyncio
async def test_websearch_invalid_backend(tool_context):
    """Test that invalid backend names are handled properly."""
    tool = WebSearchTool()

    result = await tool.execute(
        {
            "query": "test",
            "backend": "nonexistent",
        },
        tool_context,
    )

    assert result["success"] is False
    assert "unknown backend" in result["error"].lower()


@pytest.mark.asyncio
async def test_webfetch_invalid_url(tool_context):
    """Test that invalid URLs are handled properly."""
    tool = WebFetchTool()

    result = await tool.execute(
        {
            "url": "not-a-valid-url",
        },
        tool_context,
    )

    assert result["success"] is False
    assert "http" in result["error"].lower()
