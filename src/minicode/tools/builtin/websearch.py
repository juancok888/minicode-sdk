"""WebSearch tool with configurable search backends."""

import json
from typing import Any, Dict, List, Optional

import httpx

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool

DEFAULT_NUM_RESULTS = 8
DEFAULT_TIMEOUT = 25  # 25 seconds


class SearchBackend:
    """Base class for search backends."""

    async def search(
        self,
        query: str,
        num_results: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute search query.

        Args:
            query: Search query string
            num_results: Number of results to return
            **kwargs: Additional backend-specific parameters

        Returns:
            Dictionary with search results
        """
        raise NotImplementedError


class ExaSearchBackend(SearchBackend):
    """Exa.ai search backend using MCP protocol."""

    BASE_URL = "https://mcp.exa.ai"
    ENDPOINT = "/mcp"

    async def search(
        self,
        query: str,
        num_results: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute Exa search.

        Args:
            query: Search query
            num_results: Number of results
            **kwargs: Additional parameters (livecrawl, type, contextMaxCharacters)

        Returns:
            Search results
        """
        # Build arguments with proper defaults (no None values)
        search_type = kwargs.get("type") or "auto"
        livecrawl = kwargs.get("livecrawl") or "fallback"

        arguments = {
            "query": query,
            "type": search_type,
            "numResults": num_results,
            "livecrawl": livecrawl,
        }

        # Only add contextMaxCharacters if specified
        context_max = kwargs.get("contextMaxCharacters")
        if context_max is not None:
            arguments["contextMaxCharacters"] = context_max

        search_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "web_search_exa",
                "arguments": arguments,
            },
        }

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(
                f"{self.BASE_URL}{self.ENDPOINT}",
                json=search_request,
                headers={
                    "accept": "application/json, text/event-stream",
                    "content-type": "application/json",
                },
            )

            response.raise_for_status()
            response_text = response.text

            # Parse SSE response
            lines = response_text.split("\n")
            for line in lines:
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if (
                        data.get("result")
                        and data["result"].get("content")
                        and len(data["result"]["content"]) > 0
                    ):
                        return {
                            "success": True,
                            "content": data["result"]["content"][0]["text"],
                            "backend": "exa",
                        }

            return {
                "success": False,
                "error": "No search results found",
                "backend": "exa",
            }


class GoogleSearchBackend(SearchBackend):
    """Google Custom Search API backend.

    Requires environment variables:
    - GOOGLE_API_KEY: Google API key
    - GOOGLE_CSE_ID: Custom Search Engine ID
    """

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    async def search(
        self,
        query: str,
        num_results: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute Google Custom Search.

        Args:
            query: Search query string.
            num_results: Number of results to return (max 10 per request).
            **kwargs: Additional search parameters.

        Returns:
            Search results dict with success status and content.
        """
        import os

        api_key = os.environ.get("GOOGLE_API_KEY")
        cse_id = os.environ.get("GOOGLE_CSE_ID")

        if not api_key or not cse_id:
            import warnings
            warnings.warn(
                "Google Search requires GOOGLE_API_KEY and GOOGLE_CSE_ID "
                "environment variables to be set."
            )
            return {
                "success": False,
                "error": "GOOGLE_API_KEY or GOOGLE_CSE_ID not configured",
                "backend": "google",
            }

        try:
            params = {
                "key": api_key,
                "cx": cse_id,
                "q": query,
                "num": min(num_results, 10),
            }

            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            items = data.get("items", [])
            if not items:
                return {
                    "success": False,
                    "error": "No search results found",
                    "backend": "google",
                }

            # Format results
            formatted_results = []
            for item in items:
                formatted_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                })

            # Convert to text format
            content_parts = []
            for i, result in enumerate(formatted_results, 1):
                content_parts.append(f"{i}. {result['title']}")
                content_parts.append(f"   URL: {result['url']}")
                content_parts.append(f"   {result['snippet']}")
                content_parts.append("")

            return {
                "success": True,
                "content": "\n".join(content_parts),
                "results": formatted_results,
                "backend": "google",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Google search failed: {str(e)}",
                "backend": "google",
            }


class BingSearchBackend(SearchBackend):
    """Bing Search API backend.

    Requires environment variable:
    - BING_API_KEY: Bing Search API key (from Azure Cognitive Services)
    """

    BASE_URL = "https://api.bing.microsoft.com/v7.0/search"

    async def search(
        self,
        query: str,
        num_results: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute Bing Search.

        Args:
            query: Search query string.
            num_results: Number of results to return.
            **kwargs: Additional search parameters.

        Returns:
            Search results dict with success status and content.
        """
        import os

        api_key = os.environ.get("BING_API_KEY")

        if not api_key:
            import warnings
            warnings.warn(
                "Bing Search requires BING_API_KEY environment variable to be set."
            )
            return {
                "success": False,
                "error": "BING_API_KEY not configured",
                "backend": "bing",
            }

        try:
            headers = {"Ocp-Apim-Subscription-Key": api_key}
            params = {
                "q": query,
                "count": num_results,
                "textDecorations": True,
                "textFormat": "HTML",
            }

            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.get(
                    self.BASE_URL, headers=headers, params=params
                )
                response.raise_for_status()
                data = response.json()

            web_pages = data.get("webPages", {}).get("value", [])
            if not web_pages:
                return {
                    "success": False,
                    "error": "No search results found",
                    "backend": "bing",
                }

            # Format results
            formatted_results = []
            for item in web_pages:
                formatted_results.append({
                    "title": item.get("name", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                })

            # Convert to text format
            content_parts = []
            for i, result in enumerate(formatted_results, 1):
                content_parts.append(f"{i}. {result['title']}")
                content_parts.append(f"   URL: {result['url']}")
                content_parts.append(f"   {result['snippet']}")
                content_parts.append("")

            return {
                "success": True,
                "content": "\n".join(content_parts),
                "results": formatted_results,
                "backend": "bing",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Bing search failed: {str(e)}",
                "backend": "bing",
            }


class DuckDuckGoSearchBackend(SearchBackend):
    """DuckDuckGo search backend (requires ddgs package)."""

    async def search(
        self,
        query: str,
        num_results: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute DuckDuckGo search.

        Args:
            query: Search query string.
            num_results: Number of results to return.
            **kwargs: Additional search parameters.

        Returns:
            Search results dict with success status and content.
        """
        # Try new package name first, then fall back to old name
        DDGS = None
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                import warnings
                warnings.warn(
                    "ddgs package not installed. "
                    "Install with: pip install ddgs"
                )
                return {
                    "success": False,
                    "error": "ddgs package not installed",
                    "backend": "duckduckgo",
                }

        try:
            ddgs = DDGS()
            results = list(ddgs.text(query, max_results=num_results))

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                })

            # Convert to text format
            content_parts = []
            for i, result in enumerate(formatted_results, 1):
                content_parts.append(f"{i}. {result['title']}")
                content_parts.append(f"   URL: {result['url']}")
                content_parts.append(f"   {result['snippet']}")
                content_parts.append("")

            return {
                "success": True,
                "content": "\n".join(content_parts),
                "results": formatted_results,
                "backend": "duckduckgo",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"DuckDuckGo search failed: {str(e)}",
                "backend": "duckduckgo",
            }


def _check_backend_availability() -> Dict[str, bool]:
    """Check which search backends are available.

    Returns:
        Dict mapping backend names to their availability status.
    """
    import os

    availability = {
        "exa": True,  # Exa is always available (no API key required for MCP)
        "google": bool(
            os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_CSE_ID")
        ),
        "bing": bool(os.environ.get("BING_API_KEY")),
        "duckduckgo": False,
    }

    # Check if ddgs or duckduckgo-search package is installed
    try:
        import ddgs  # noqa: F401
        availability["duckduckgo"] = True
    except ImportError:
        try:
            import duckduckgo_search  # noqa: F401
            availability["duckduckgo"] = True
        except ImportError:
            pass

    return availability


class WebSearchTool(BaseTool):
    """Tool for web search with configurable backends.

    Dynamically detects available backends based on installed packages
    and configured API keys.
    """

    # Backend descriptions for documentation
    _BACKEND_DESCRIPTIONS = {
        "exa": (
            "exa: Exa.ai search via MCP protocol\n"
            "  - Supports livecrawl mode (fallback/preferred)\n"
            "  - Search types: auto, fast, deep\n"
            "  - Context optimization for LLMs"
        ),
        "google": (
            "google: Google Custom Search API\n"
            "  - Max 10 results per request"
        ),
        "bing": "bing: Bing Search API",
        "duckduckgo": "duckduckgo: DuckDuckGo search",
    }

    def __init__(self, default_backend: str = "duckduckgo"):
        """Initialize WebSearch tool.

        Args:
            default_backend: Default search backend to use
        """
        self._default_backend = default_backend
        self._backends = {
            "exa": ExaSearchBackend(),
            "google": GoogleSearchBackend(),
            "bing": BingSearchBackend(),
            "duckduckgo": DuckDuckGoSearchBackend(),
        }

    def _get_available_backends(self) -> List[str]:
        """Get list of currently available backends.

        Returns:
            List of available backend names.
        """
        availability = _check_backend_availability()
        return [name for name, available in availability.items() if available]

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "websearch"

    @property
    def description(self) -> str:
        """Get the tool description with only available backends."""
        available = self._get_available_backends()

        # Build backend descriptions for available backends only
        backend_docs = []
        for backend_name in available:
            if backend_name in self._BACKEND_DESCRIPTIONS:
                backend_docs.append(f"- {self._BACKEND_DESCRIPTIONS[backend_name]}")

        # Determine default backend (use first available if default is not available)
        default = self._default_backend if self._default_backend in available else (
            available[0] if available else "exa"
        )

        return f"""Search the web using configurable search backends.

Features:
- Multiple search backends ({', '.join(available)})
- Configurable number of results
- Backend-specific options (livecrawl, search type, etc.)
- Structured search results with URLs and snippets

Available Backends:
{chr(10).join(backend_docs)}

Usage notes:
- Default backend is {default}
- Results are limited to specified number (default: {DEFAULT_NUM_RESULTS})
- Exa backend provides LLM-optimized context

Examples:
- Basic search: query="Python tutorials"
- Specify results: query="AI news", num_results=10"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema with only available backends."""
        available = self._get_available_backends()

        # Determine default backend
        default = self._default_backend if self._default_backend in available else (
            available[0] if available else "exa"
        )

        schema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "num_results": {
                    "type": "integer",
                    "description": f"Number of search results to return (default: {DEFAULT_NUM_RESULTS})",
                    "default": DEFAULT_NUM_RESULTS,
                },
                "backend": {
                    "type": "string",
                    "enum": available if available else ["exa"],
                    "description": f"Search backend to use (default: {default})",
                    "default": default,
                },
            },
            "required": ["query"],
        }

        # Only add Exa-specific parameters if Exa is available
        if "exa" in available:
            schema["properties"]["livecrawl"] = {
                "type": "string",
                "enum": ["fallback", "preferred"],
                "description": "Exa only: Live crawl mode - fallback (default) or preferred",
                "default": "fallback",
            }
            schema["properties"]["type"] = {
                "type": "string",
                "enum": ["auto", "fast", "deep"],
                "description": "Exa only: Search type - auto (default), fast, or deep",
                "default": "auto",
            }
            schema["properties"]["contextMaxCharacters"] = {
                "type": "integer",
                "description": "Exa only: Maximum characters for context (default: 10000)",
            }

        return schema

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute web search.

        Args:
            params: Search parameters
            context: Tool execution context

        Returns:
            Dictionary containing search results
        """
        query = params.get("query")
        if not query:
            return {
                "success": False,
                "error": "query parameter is required",
            }

        backend_name = params.get("backend", self._default_backend)
        num_results = params.get("num_results", DEFAULT_NUM_RESULTS)

        # Get backend
        backend = self._backends.get(backend_name)
        if not backend:
            return {
                "success": False,
                "error": f"Unknown backend: {backend_name}",
            }

        try:
            # Execute search with backend-specific parameters
            result = await backend.search(
                query=query,
                num_results=num_results,
                livecrawl=params.get("livecrawl"),
                type=params.get("type"),
                contextMaxCharacters=params.get("contextMaxCharacters"),
            )

            if result.get("success"):
                return {
                    "success": True,
                    "content": result["content"],
                    "query": query,
                    "backend": backend_name,
                    "num_results": num_results,
                }
            else:
                return result

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": f"Search request timed out after {DEFAULT_TIMEOUT} seconds",
                "backend": backend_name,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "backend": backend_name,
            }
