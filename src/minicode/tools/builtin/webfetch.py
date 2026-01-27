"""WebFetch tool for fetching and converting web content."""

import asyncio
from typing import Any, Dict, Optional

import html2text
import httpx
from bs4 import BeautifulSoup

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool

MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB
DEFAULT_TIMEOUT = 30  # 30 seconds
MAX_TIMEOUT = 120  # 2 minutes


class WebFetchTool(BaseTool):
    """Tool for fetching web content with format conversion.

    Supports fetching URLs and converting to different formats:
    - text: Plain text extraction from HTML
    - markdown: Convert HTML to Markdown
    - html: Raw HTML content
    """

    def __init__(self, default_timeout: int = DEFAULT_TIMEOUT):
        """Initialize WebFetch tool.

        Args:
            default_timeout: Default timeout in seconds.
        """
        self._default_timeout = default_timeout

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "webfetch"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return """Fetch content from URLs with format conversion.

Features:
- Fetches content from HTTP/HTTPS URLs
- Converts HTML to Markdown or plain text
- Supports custom timeouts (max 120 seconds)
- Size limit: 5MB maximum response size
- Automatic User-Agent and Accept headers

Usage notes:
- URL must start with http:// or https://
- Default format is markdown
- HTML is automatically converted based on format parameter
- Includes timeout protection

Examples:
- Fetch as markdown: url="https://example.com", format="markdown"
- Fetch as text: url="https://example.com", format="text"
- Fetch as HTML: url="https://example.com", format="html"
- Custom timeout: url="https://example.com", timeout=60"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch content from",
                },
                "format": {
                    "type": "string",
                    "enum": ["text", "markdown", "html"],
                    "description": "Output format (text, markdown, or html)",
                    "default": "markdown",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (max 120)",
                    "default": DEFAULT_TIMEOUT,
                },
            },
            "required": ["url"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute web fetch.

        Args:
            params: Fetch parameters
            context: Tool execution context

        Returns:
            Dictionary containing fetched content
        """
        url = params.get("url")
        if not url:
            return {
                "success": False,
                "error": "url parameter is required",
            }

        # Validate URL
        if not url.startswith("http://") and not url.startswith("https://"):
            return {
                "success": False,
                "error": "URL must start with http:// or https://",
            }

        output_format = params.get("format", "markdown")
        timeout = min(params.get("timeout", self._default_timeout), MAX_TIMEOUT)

        try:
            # Build Accept header based on requested format
            accept_header = self._get_accept_header(output_format)

            # Fetch content
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                        "Accept": accept_header,
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                    follow_redirects=True,
                )

                response.raise_for_status()

                # Check content length
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_RESPONSE_SIZE:
                    return {
                        "success": False,
                        "error": "Response too large (exceeds 5MB limit)",
                    }

                content = response.text
                if len(content.encode("utf-8")) > MAX_RESPONSE_SIZE:
                    return {
                        "success": False,
                        "error": "Response too large (exceeds 5MB limit)",
                    }

                content_type = response.headers.get("content-type", "")
                title = f"{url} ({content_type})"

                # Process content based on format
                output = self._process_content(
                    content=content,
                    content_type=content_type,
                    output_format=output_format,
                )

                return {
                    "success": True,
                    "content": output,
                    "title": title,
                    "url": str(response.url),  # Final URL after redirects
                    "content_type": content_type,
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": f"Request timed out after {timeout} seconds",
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP error {e.response.status_code}: {e.response.reason_phrase}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"WebFetch failed: {str(e)}",
            }

    def _get_accept_header(self, output_format: str) -> str:
        """Get Accept header based on output format.

        Args:
            output_format: Desired output format

        Returns:
            Accept header string with quality parameters
        """
        if output_format == "markdown":
            return "text/markdown;q=1.0, text/x-markdown;q=0.9, text/plain;q=0.8, text/html;q=0.7, */*;q=0.1"
        elif output_format == "text":
            return "text/plain;q=1.0, text/markdown;q=0.9, text/html;q=0.8, */*;q=0.1"
        elif output_format == "html":
            return "text/html;q=1.0, application/xhtml+xml;q=0.9, text/plain;q=0.8, text/markdown;q=0.7, */*;q=0.1"
        else:
            return "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"

    def _process_content(
        self,
        content: str,
        content_type: str,
        output_format: str,
    ) -> str:
        """Process content based on format.

        Args:
            content: Raw content
            content_type: Content-Type header value
            output_format: Desired output format

        Returns:
            Processed content
        """
        is_html = "text/html" in content_type

        if output_format == "markdown" and is_html:
            return self._convert_html_to_markdown(content)
        elif output_format == "text" and is_html:
            return self._extract_text_from_html(content)
        else:
            return content

    def _convert_html_to_markdown(self, html: str) -> str:
        """Convert HTML to Markdown.

        Args:
            html: HTML content

        Returns:
            Markdown content
        """
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = False
        converter.ignore_emphasis = False
        converter.body_width = 0  # Don't wrap lines
        converter.single_line_break = False

        return converter.handle(html)

    def _extract_text_from_html(self, html: str) -> str:
        """Extract plain text from HTML.

        Args:
            html: HTML content

        Returns:
            Plain text content
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "noscript", "iframe", "object", "embed"]):
            element.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)

        return text
