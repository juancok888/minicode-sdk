"""Tests for web tools (WebFetch, WebSearch)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from minicode.session.message import ToolContext
from minicode.tools.builtin import WebFetchTool, WebSearchTool


@pytest.fixture
def tool_context():
    """Create a tool context for testing."""
    return ToolContext(agent_name="test", session_id="test-session")


# WebFetchTool Tests


@pytest.mark.asyncio
async def test_webfetch_missing_url(tool_context):
    """Test WebFetch with missing URL."""
    tool = WebFetchTool()
    result = await tool.execute({}, tool_context)

    assert result["success"] is False
    assert "required" in result["error"].lower()


@pytest.mark.asyncio
async def test_webfetch_invalid_url_scheme(tool_context):
    """Test WebFetch with invalid URL scheme."""
    tool = WebFetchTool()
    result = await tool.execute(
        {"url": "ftp://example.com"},
        tool_context,
    )

    assert result["success"] is False
    assert "http" in result["error"].lower()


@pytest.mark.asyncio
async def test_webfetch_html_to_markdown(tool_context):
    """Test WebFetch HTML to Markdown conversion."""
    tool = WebFetchTool()

    html_content = """
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Hello World</h1>
        <p>This is a <strong>test</strong> paragraph.</p>
        <a href="https://example.com">Link</a>
    </body>
    </html>
    """

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mock_response.text = html_content
    mock_response.url = "https://example.com"
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await tool.execute(
            {"url": "https://example.com", "format": "markdown"},
            tool_context,
        )

        assert result["success"] is True
        assert "Hello World" in result["content"]
        assert "test" in result["content"]
        assert "example.com" in result["content"]


@pytest.mark.asyncio
async def test_webfetch_html_to_text(tool_context):
    """Test WebFetch HTML to text extraction."""
    tool = WebFetchTool()

    html_content = """
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Hello World</p>
        <script>console.log('should be removed');</script>
        <style>.test { color: red; }</style>
    </body>
    </html>
    """

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = html_content
    mock_response.url = "https://example.com"
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await tool.execute(
            {"url": "https://example.com", "format": "text"},
            tool_context,
        )

        assert result["success"] is True
        assert "Hello World" in result["content"]
        assert "console.log" not in result["content"]
        assert "color: red" not in result["content"]


@pytest.mark.asyncio
async def test_webfetch_raw_html(tool_context):
    """Test WebFetch raw HTML output."""
    tool = WebFetchTool()

    html_content = "<html><body><h1>Test</h1></body></html>"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = html_content
    mock_response.url = "https://example.com"
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await tool.execute(
            {"url": "https://example.com", "format": "html"},
            tool_context,
        )

        assert result["success"] is True
        assert result["content"] == html_content


@pytest.mark.asyncio
async def test_webfetch_timeout(tool_context):
    """Test WebFetch timeout handling."""
    tool = WebFetchTool()

    with patch("httpx.AsyncClient") as mock_client:
        import httpx

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )

        result = await tool.execute(
            {"url": "https://example.com", "timeout": 1},
            tool_context,
        )

        assert result["success"] is False
        assert "timed out" in result["error"].lower()


@pytest.mark.asyncio
async def test_webfetch_http_error(tool_context):
    """Test WebFetch HTTP error handling."""
    tool = WebFetchTool()

    with patch("httpx.AsyncClient") as mock_client:
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "404", request=MagicMock(), response=mock_response
            )
        )

        result = await tool.execute(
            {"url": "https://example.com/notfound"},
            tool_context,
        )

        assert result["success"] is False
        assert "404" in result["error"]


@pytest.mark.asyncio
async def test_webfetch_size_limit(tool_context):
    """Test WebFetch size limit enforcement."""
    tool = WebFetchTool()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/plain", "content-length": "6000000"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await tool.execute(
            {"url": "https://example.com/large"},
            tool_context,
        )

        assert result["success"] is False
        assert "too large" in result["error"].lower()


# WebSearchTool Tests


@pytest.mark.asyncio
async def test_websearch_missing_query(tool_context):
    """Test WebSearch with missing query."""
    tool = WebSearchTool()
    result = await tool.execute({}, tool_context)

    assert result["success"] is False
    assert "required" in result["error"].lower()


@pytest.mark.asyncio
async def test_websearch_unknown_backend(tool_context):
    """Test WebSearch with unknown backend."""
    tool = WebSearchTool()
    result = await tool.execute(
        {"query": "test", "backend": "unknown"},
        tool_context,
    )

    assert result["success"] is False
    assert "unknown backend" in result["error"].lower()


@pytest.mark.asyncio
async def test_websearch_exa_success(tool_context):
    """Test WebSearch with Exa backend success."""
    tool = WebSearchTool(default_backend="exa")

    # Mock SSE response from Exa
    sse_response = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"Search results here"}]}}\n'

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = sse_response
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await tool.execute(
            {"query": "Python tutorials", "num_results": 5},
            tool_context,
        )

        assert result["success"] is True
        assert result["content"] == "Search results here"
        assert result["backend"] == "exa"
        assert result["query"] == "Python tutorials"


@pytest.mark.asyncio
async def test_websearch_exa_with_options(tool_context):
    """Test WebSearch with Exa backend and additional options."""
    tool = WebSearchTool(default_backend="exa")

    sse_response = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"Deep search results"}]}}\n'

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = sse_response
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        result = await tool.execute(
            {
                "query": "AI research",
                "type": "deep",
                "livecrawl": "preferred",
                "contextMaxCharacters": 15000,
            },
            tool_context,
        )

        assert result["success"] is True
        # Verify the request included the options
        call_args = mock_post.call_args
        request_json = call_args[1]["json"]
        assert request_json["params"]["arguments"]["type"] == "deep"
        assert request_json["params"]["arguments"]["livecrawl"] == "preferred"
        assert request_json["params"]["arguments"]["contextMaxCharacters"] == 15000


@pytest.mark.asyncio
async def test_websearch_exa_no_results(tool_context):
    """Test WebSearch with Exa backend returning no results."""
    tool = WebSearchTool(default_backend="exa")

    # Empty SSE response
    sse_response = ""

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = sse_response
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await tool.execute(
            {"query": "nonexistent query 12345"},
            tool_context,
        )

        assert result["success"] is False
        assert "no search results" in result["error"].lower()


@pytest.mark.asyncio
async def test_websearch_timeout(tool_context):
    """Test WebSearch timeout handling."""
    tool = WebSearchTool()

    with patch("httpx.AsyncClient") as mock_client:
        import httpx

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )

        result = await tool.execute(
            {"query": "test query"},
            tool_context,
        )

        assert result["success"] is False
        assert "timed out" in result["error"].lower()


@pytest.mark.asyncio
async def test_websearch_duckduckgo_not_implemented(tool_context):
    """Test WebSearch DuckDuckGo backend placeholder."""
    tool = WebSearchTool()

    result = await tool.execute(
        {"query": "test", "backend": "duckduckgo"},
        tool_context,
    )

    assert result["success"] is False
    assert "not implemented" in result["error"].lower()


# Tool Properties Tests


def test_webfetch_tool_properties():
    """Test WebFetchTool properties."""
    tool = WebFetchTool()
    assert tool.name == "webfetch"
    assert len(tool.description) > 0
    assert "url" in tool.parameters_schema["properties"]
    assert "format" in tool.parameters_schema["properties"]


def test_websearch_tool_properties():
    """Test WebSearchTool properties."""
    tool = WebSearchTool()
    assert tool.name == "websearch"
    assert len(tool.description) > 0
    assert "query" in tool.parameters_schema["properties"]
    assert "backend" in tool.parameters_schema["properties"]
