"""MCP client implementation."""

from typing import Any, Dict, List, Optional

from minicode.mcp.transport import HTTPTransport, MCPTransport, StdioTransport
from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool


class MCPTool(BaseTool):
    """Wrapper for MCP tools to work with minicode's tool system."""

    def __init__(
        self,
        mcp_client: "MCPClient",
        tool_name: str,
        tool_description: str,
        tool_schema: Dict[str, Any],
    ):
        """Initialize MCP tool wrapper.

        Args:
            mcp_client: The MCP client instance
            tool_name: Name of the tool
            tool_description: Description of the tool
            tool_schema: JSON Schema for tool parameters
        """
        self._mcp_client = mcp_client
        self._name = tool_name
        self._description = tool_description
        self._schema = tool_schema

    @property
    def name(self) -> str:
        """Get the tool name."""
        return self._name

    @property
    def description(self) -> str:
        """Get the tool description."""
        return self._description

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return self._schema

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute the MCP tool."""
        try:
            result = await self._mcp_client.call_tool(self._name, params)
            return {
                "success": True,
                "data": result,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


class MCPClient:
    """Client for connecting to and interacting with MCP servers.

    The MCP client manages connections to one or more MCP servers,
    discovers available tools, and provides them to agents.
    """

    def __init__(self) -> None:
        """Initialize MCP client."""
        self._servers: Dict[str, MCPTransport] = {}
        self._tools: Dict[str, MCPTool] = {}

    async def add_server(
        self,
        name: str,
        command: Optional[List[str]] = None,
        url: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Add an MCP server and discover its tools.

        Args:
            name: Identifier for this server
            command: Command to launch stdio-based MCP server (mutually exclusive with url)
            url: URL for HTTP-based MCP server (mutually exclusive with command)
            env: Environment variables for stdio server
            headers: HTTP headers for HTTP server

        Raises:
            ValueError: If neither command nor url is provided, or both are provided
        """
        if command and url:
            raise ValueError("Cannot specify both command and url")

        if not command and not url:
            raise ValueError("Must specify either command or url")

        # Create transport
        if command:
            transport = StdioTransport(command, env)
        else:
            transport = HTTPTransport(url, headers)  # type: ignore

        # Connect to server
        await transport.connect()
        self._servers[name] = transport

        # Discover tools
        await self._discover_tools(name, transport)

    async def remove_server(self, name: str) -> None:
        """Remove an MCP server and its tools.

        Args:
            name: Identifier of the server to remove
        """
        if name not in self._servers:
            return

        # Disconnect from server
        transport = self._servers[name]
        await transport.disconnect()
        del self._servers[name]

        # Remove tools from this server
        tools_to_remove = [
            tool_name for tool_name in self._tools.keys() if tool_name.startswith(f"{name}:")
        ]
        for tool_name in tools_to_remove:
            del self._tools[tool_name]

    async def _discover_tools(self, server_name: str, transport: MCPTransport) -> None:
        """Discover tools from an MCP server.

        Args:
            server_name: Name of the server
            transport: Transport to use for communication
        """
        try:
            # Call list_tools method
            result = await transport.send_request("tools/list")
            tools = result.get("tools", [])

            # Register each tool
            for tool_def in tools:
                tool_name = tool_def.get("name", "")
                tool_description = tool_def.get("description", "")
                tool_schema = tool_def.get("inputSchema", {})

                # Prefix tool name with server name to avoid conflicts
                prefixed_name = f"{server_name}:{tool_name}"

                mcp_tool = MCPTool(
                    mcp_client=self,
                    tool_name=tool_name,  # Keep original name for MCP calls
                    tool_description=tool_description,
                    tool_schema=tool_schema,
                )

                self._tools[prefixed_name] = mcp_tool

        except Exception as e:
            # Note: Tool discovery failure is not fatal - server may not support it yet
            # In production, consider logging this error for debugging
            # TODO: Add logging support
            pass

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Call a tool on the appropriate MCP server.

        Args:
            tool_name: Name of the tool (unprefixed)
            params: Parameters for the tool

        Returns:
            The result from the tool execution
        """
        # Find the right server and transport
        # This assumes tool_name is the original name without server prefix
        for server_name, transport in self._servers.items():
            try:
                result = await transport.send_request(
                    "tools/call",
                    {"name": tool_name, "arguments": params},
                )
                return result.get("content", [])
            except Exception:
                continue

        raise RuntimeError(f"No server found for tool: {tool_name}")

    def get_tools(self) -> List[BaseTool]:
        """Get all discovered MCP tools.

        Returns:
            List of MCP tools wrapped as BaseTool instances
        """
        return list(self._tools.values())

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for name in list(self._servers.keys()):
            await self.remove_server(name)
