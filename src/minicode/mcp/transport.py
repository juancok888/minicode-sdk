"""MCP transport layer implementations."""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

# MCP protocol version to use
MCP_PROTOCOL_VERSION = "2024-11-05"

# Client info for initialization
MCP_CLIENT_INFO = {
    "name": "minicode",
    "version": "0.1.0",
}


class MCPTransport(ABC):
    """Abstract base class for MCP transport implementations."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the MCP server."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the MCP server."""
        pass

    @abstractmethod
    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a request to the MCP server.

        Args:
            method: The RPC method name
            params: Optional parameters for the method

        Returns:
            The response from the server
        """
        pass

    @abstractmethod
    async def send_notification(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a notification to the MCP server (no response expected).

        Args:
            method: The RPC method name
            params: Optional parameters for the method
        """
        pass

    async def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP connection following the protocol lifecycle.

        Returns:
            The server's initialization response with capabilities.
        """
        # Send initialize request
        result = await self.send_request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {},
                },
                "clientInfo": MCP_CLIENT_INFO,
            },
        )

        # Send initialized notification
        await self.send_notification("notifications/initialized")

        return result


class StdioTransport(MCPTransport):
    """Stdio transport for MCP servers that communicate via stdin/stdout.

    This transport launches an MCP server as a subprocess and communicates
    with it via standard input/output streams.
    """

    def __init__(self, command: List[str], env: Optional[Dict[str, str]] = None):
        """Initialize stdio transport.

        Args:
            command: Command and arguments to launch the MCP server
            env: Optional environment variables
        """
        self.command = command
        self.env = env
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._initialized = False

    async def connect(self) -> None:
        """Launch the MCP server process and perform protocol initialization."""
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env,
        )

        # Wait for the server to be ready (some servers need startup time)
        await asyncio.sleep(1.0)

        # Perform MCP protocol initialization
        await self.initialize()
        self._initialized = True

    async def disconnect(self) -> None:
        """Terminate the MCP server process."""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except ProcessLookupError:
                # Process already terminated
                pass
            self.process = None

    async def send_notification(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a JSON-RPC notification to the MCP server (no response expected)."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Transport not connected")

        notification = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            notification["params"] = params

        notification_json = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_json.encode())
        await self.process.stdin.drain()

    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError("Transport not connected")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }

        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        # Read response, handling any notifications that may come before the response
        while True:
            response_line = await self.process.stdout.readline()
            if not response_line:
                raise RuntimeError("Server closed connection unexpectedly")
            response = json.loads(response_line.decode())

            # Skip notifications (messages without id)
            if "id" not in response:
                continue

            if "error" in response:
                raise RuntimeError(f"MCP error: {response['error']}")

            return response.get("result", {})


class HTTPTransport(MCPTransport):
    """HTTP transport for MCP servers accessible via HTTP/HTTPS.

    This transport communicates with MCP servers over HTTP.
    """

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        """Initialize HTTP transport.

        Args:
            url: Base URL of the MCP server
            headers: Optional HTTP headers
        """
        self.url = url
        self.headers = headers or {}
        self.client: Optional[httpx.AsyncClient] = None
        self._request_id = 0
        self._initialized = False
        self._session_id: Optional[str] = None

    async def connect(self) -> None:
        """Create HTTP client and perform protocol initialization."""
        self.client = httpx.AsyncClient(headers=self.headers)

        # Perform MCP protocol initialization
        await self.initialize()
        self._initialized = True

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            self._initialized = False
            self._session_id = None

    async def send_notification(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a JSON-RPC notification via HTTP (no response expected)."""
        if not self.client:
            raise RuntimeError("Transport not connected")

        notification = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            notification["params"] = params

        headers = {"Accept": "application/json, text/event-stream"}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        response = await self.client.post(self.url, json=notification, headers=headers)
        # Notifications should return 202 Accepted
        if response.status_code not in (200, 202):
            response.raise_for_status()

    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request via HTTP."""
        if not self.client:
            raise RuntimeError("Transport not connected")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }

        headers = {"Accept": "application/json, text/event-stream"}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        response = await self.client.post(self.url, json=request, headers=headers)
        response.raise_for_status()

        # Check for session ID in response headers
        if "Mcp-Session-Id" in response.headers:
            self._session_id = response.headers["Mcp-Session-Id"]

        result = response.json()

        if "error" in result:
            raise RuntimeError(f"MCP error: {result['error']}")

        return result.get("result", {})
