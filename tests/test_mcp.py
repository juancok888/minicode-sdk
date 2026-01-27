"""Tests for MCP client functionality.

This module contains both unit tests (with mocked servers) and integration tests
(with real MCP servers) for the MCP client implementation.
"""

import asyncio
import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from minicode.mcp import MCPClient
from minicode.mcp.client import MCPTool
from minicode.mcp.transport import HTTPTransport, MCPTransport, StdioTransport
from minicode.session.message import ToolContext


@pytest.fixture
def tool_context():
    """Create a tool context for testing."""
    return ToolContext(agent_name="test", session_id="test-session")


class MockTransport(MCPTransport):
    """Mock transport for unit testing."""

    def __init__(self, tools: list[Dict[str, Any]] = None):
        """Initialize mock transport.

        Args:
            tools: List of tool definitions to return from tools/list.
        """
        self._connected = False
        self._tools = tools or []
        self._call_results: Dict[str, Any] = {}

    async def connect(self) -> None:
        """Simulate connection (without initialization for unit tests)."""
        self._connected = True

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self._connected = False

    def set_tool_result(self, tool_name: str, result: Any) -> None:
        """Set the result for a specific tool call.

        Args:
            tool_name: Name of the tool.
            result: Result to return when the tool is called.
        """
        self._call_results[tool_name] = result

    async def send_notification(
        self,
        method: str,
        params: Dict[str, Any] | None = None,
    ) -> None:
        """Handle mock notifications (no-op for testing)."""
        pass

    async def send_request(
        self,
        method: str,
        params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Handle mock requests."""
        if not self._connected:
            raise RuntimeError("Transport not connected")

        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "MockServer", "version": "1.0.0"},
            }
        elif method == "tools/list":
            return {"tools": self._tools}
        elif method == "tools/call":
            tool_name = params.get("name", "") if params else ""
            if tool_name in self._call_results:
                return {"content": self._call_results[tool_name]}
            return {"content": [{"type": "text", "text": f"Mock result for {tool_name}"}]}

        return {}


# =============================================================================
# Unit Tests (with mocked transport)
# =============================================================================


class TestMCPClientUnit:
    """Unit tests for MCPClient with mocked transport."""

    @pytest.mark.asyncio
    async def test_add_server_with_mock_transport(self):
        """Test adding a server with mock transport."""
        client = MCPClient()

        mock_tools = [
            {
                "name": "echo",
                "description": "Echo the input",
                "inputSchema": {
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                },
            }
        ]

        mock_transport = MockTransport(tools=mock_tools)

        # Patch to use mock transport
        with patch.object(client, "_servers", {}) as servers:
            servers["test-server"] = mock_transport
            await mock_transport.connect()
            await client._discover_tools("test-server", mock_transport)

            tools = client.get_tools()
            assert len(tools) == 1
            assert tools[0].name == "echo"
            assert tools[0].description == "Echo the input"

    @pytest.mark.asyncio
    async def test_discover_multiple_tools(self):
        """Test discovering multiple tools from a server."""
        client = MCPClient()

        mock_tools = [
            {"name": "tool1", "description": "First tool", "inputSchema": {}},
            {"name": "tool2", "description": "Second tool", "inputSchema": {}},
            {"name": "tool3", "description": "Third tool", "inputSchema": {}},
        ]

        mock_transport = MockTransport(tools=mock_tools)
        await mock_transport.connect()
        await client._discover_tools("server1", mock_transport)
        client._servers["server1"] = mock_transport

        tools = client.get_tools()
        assert len(tools) == 3
        tool_names = {t.name for t in tools}
        assert tool_names == {"tool1", "tool2", "tool3"}

    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        """Test calling a tool successfully."""
        client = MCPClient()

        mock_transport = MockTransport(
            tools=[{"name": "add", "description": "Add numbers", "inputSchema": {}}]
        )
        mock_transport.set_tool_result("add", [{"type": "text", "text": "5"}])

        await mock_transport.connect()
        client._servers["math-server"] = mock_transport

        result = await client.call_tool("add", {"a": 2, "b": 3})
        assert result == [{"type": "text", "text": "5"}]

    @pytest.mark.asyncio
    async def test_remove_server(self):
        """Test removing a server and its tools."""
        client = MCPClient()

        mock_transport = MockTransport(
            tools=[{"name": "test_tool", "description": "Test", "inputSchema": {}}]
        )

        await mock_transport.connect()
        client._servers["server1"] = mock_transport
        await client._discover_tools("server1", mock_transport)

        assert len(client.get_tools()) == 1
        assert "server1" in client._servers

        await client.remove_server("server1")

        assert len(client.get_tools()) == 0
        assert "server1" not in client._servers

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """Test disconnecting from all servers."""
        client = MCPClient()

        transport1 = MockTransport(tools=[{"name": "t1", "description": "T1", "inputSchema": {}}])
        transport2 = MockTransport(tools=[{"name": "t2", "description": "T2", "inputSchema": {}}])

        await transport1.connect()
        await transport2.connect()

        client._servers["s1"] = transport1
        client._servers["s2"] = transport2
        await client._discover_tools("s1", transport1)
        await client._discover_tools("s2", transport2)

        assert len(client._servers) == 2
        assert len(client.get_tools()) == 2

        await client.disconnect_all()

        assert len(client._servers) == 0
        assert len(client.get_tools()) == 0


class TestMCPTool:
    """Unit tests for MCPTool wrapper."""

    @pytest.mark.asyncio
    async def test_mcp_tool_execute_success(self, tool_context):
        """Test MCPTool execute returns success."""
        mock_client = MagicMock(spec=MCPClient)
        mock_client.call_tool = AsyncMock(return_value=[{"type": "text", "text": "result"}])

        tool = MCPTool(
            mcp_client=mock_client,
            tool_name="test_tool",
            tool_description="A test tool",
            tool_schema={"type": "object"},
        )

        result = await tool.execute({"param": "value"}, tool_context)

        assert result["success"] is True
        assert result["data"] == [{"type": "text", "text": "result"}]
        mock_client.call_tool.assert_called_once_with("test_tool", {"param": "value"})

    @pytest.mark.asyncio
    async def test_mcp_tool_execute_failure(self, tool_context):
        """Test MCPTool execute handles errors."""
        mock_client = MagicMock(spec=MCPClient)
        mock_client.call_tool = AsyncMock(side_effect=RuntimeError("Connection failed"))

        tool = MCPTool(
            mcp_client=mock_client,
            tool_name="failing_tool",
            tool_description="A failing tool",
            tool_schema={},
        )

        result = await tool.execute({}, tool_context)

        assert result["success"] is False
        assert "Connection failed" in result["error"]

    def test_mcp_tool_properties(self):
        """Test MCPTool property accessors."""
        mock_client = MagicMock(spec=MCPClient)

        tool = MCPTool(
            mcp_client=mock_client,
            tool_name="my_tool",
            tool_description="My description",
            tool_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        )

        assert tool.name == "my_tool"
        assert tool.description == "My description"
        assert tool.parameters_schema == {"type": "object", "properties": {"x": {"type": "string"}}}


class TestHTTPTransport:
    """Unit tests for HTTP transport."""

    @pytest.mark.asyncio
    async def test_http_transport_client_creation(self):
        """Test HTTP transport client creation without network connection."""
        transport = HTTPTransport("http://localhost:8080/mcp")

        assert transport.client is None
        # Create client directly without initialization (to avoid network call)
        transport.client = httpx.AsyncClient(headers=transport.headers)
        assert transport.client is not None
        await transport.disconnect()
        assert transport.client is None

    @pytest.mark.asyncio
    async def test_http_transport_not_connected_error(self):
        """Test HTTP transport raises error when not connected."""
        transport = HTTPTransport("http://localhost:8080/mcp")

        with pytest.raises(RuntimeError, match="Transport not connected"):
            await transport.send_request("tools/list")


class TestStdioTransport:
    """Unit tests for Stdio transport."""

    @pytest.mark.asyncio
    async def test_stdio_transport_not_connected_error(self):
        """Test Stdio transport raises error when not connected."""
        transport = StdioTransport(["echo", "test"])

        with pytest.raises(RuntimeError, match="Transport not connected"):
            await transport.send_request("tools/list")


class TestMCPClientValidation:
    """Tests for MCPClient input validation."""

    @pytest.mark.asyncio
    async def test_add_server_requires_command_or_url(self):
        """Test that add_server requires either command or url."""
        client = MCPClient()

        with pytest.raises(ValueError, match="Must specify either command or url"):
            await client.add_server(name="test")

    @pytest.mark.asyncio
    async def test_add_server_rejects_both_command_and_url(self):
        """Test that add_server rejects both command and url."""
        client = MCPClient()

        with pytest.raises(ValueError, match="Cannot specify both command and url"):
            await client.add_server(
                name="test",
                command=["echo", "test"],
                url="http://localhost:8080/mcp",
            )


# =============================================================================
# Integration Tests (with real MCP servers)
# =============================================================================


def _check_npx_available() -> bool:
    """Check if npx is available for running MCP servers."""
    import shutil

    return shutil.which("npx") is not None


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_mcp_stdio_server_with_memory():
    """Test MCP client with the official @modelcontextprotocol/server-memory.

    This test uses the official MCP Memory server which provides knowledge graph
    capabilities. It requires npx to be installed.

    To run this test:
        pytest tests/test_mcp.py::test_mcp_stdio_server_with_memory -v -s
    """
    if not _check_npx_available():
        pytest.skip("npx not available - install Node.js to run this test")

    client = MCPClient()

    try:
        await client.add_server(
            name="memory-server",
            command=["npx", "-y", "@modelcontextprotocol/server-memory"],
        )

        tools = client.get_tools()
        print(f"\nDiscovered {len(tools)} tools from Memory server:")
        for tool in tools:
            desc = tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
            print(f"  - {tool.name}: {desc}")

        assert len(tools) > 0, "Memory server should provide at least one tool"

        # Verify expected tools exist
        tool_names = {t.name for t in tools}
        assert "read_graph" in tool_names, "Memory server should have read_graph tool"

    finally:
        await client.disconnect_all()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_mcp_call_memory_tool(tool_context):
    """Test calling a tool on the MCP Memory server.

    To run this test:
        pytest tests/test_mcp.py::test_mcp_call_memory_tool -v -s
    """
    if not _check_npx_available():
        pytest.skip("npx not available - install Node.js to run this test")

    client = MCPClient()

    try:
        await client.add_server(
            name="memory-server",
            command=["npx", "-y", "@modelcontextprotocol/server-memory"],
        )

        tools = client.get_tools()
        if not tools:
            pytest.skip("No tools available on Memory server")

        # Find read_graph tool (doesn't require parameters)
        tool = None
        for t in tools:
            if t.name == "read_graph":
                tool = t
                break

        if not tool:
            tool = tools[0]

        print(f"\nCalling tool: {tool.name}")
        print(f"Schema: {tool.parameters_schema}")

        # Execute the tool
        result = await tool.execute({}, tool_context)
        print(f"Result: {result}")

        assert "success" in result
        assert result["success"] is True

    finally:
        await client.disconnect_all()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_mcp_server_reconnection():
    """Test that we can reconnect to a server after disconnecting.

    To run this test:
        pytest tests/test_mcp.py::test_mcp_server_reconnection -v -s
    """
    if not _check_npx_available():
        pytest.skip("npx not available - install Node.js to run this test")

    client = MCPClient()

    try:
        # First connection
        await client.add_server(
            name="memory-server",
            command=["npx", "-y", "@modelcontextprotocol/server-memory"],
        )
        first_tools = client.get_tools()
        first_count = len(first_tools)

        # Disconnect
        await client.remove_server("memory-server")
        assert len(client.get_tools()) == 0

        # Reconnect
        await client.add_server(
            name="memory-server",
            command=["npx", "-y", "@modelcontextprotocol/server-memory"],
        )
        second_tools = client.get_tools()
        second_count = len(second_tools)

        # Should discover the same number of tools
        assert first_count == second_count

    finally:
        await client.disconnect_all()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_mcp_multiple_stdio_servers():
    """Test connecting to multiple MCP servers simultaneously.

    This test connects to two Memory server instances (as different "servers").

    To run this test:
        pytest tests/test_mcp.py::test_mcp_multiple_stdio_servers -v -s
    """
    if not _check_npx_available():
        pytest.skip("npx not available - install Node.js to run this test")

    client = MCPClient()

    try:
        # Connect to first Memory server instance
        await client.add_server(
            name="memory-server-1",
            command=["npx", "-y", "@modelcontextprotocol/server-memory"],
        )

        # Connect to second Memory server instance
        await client.add_server(
            name="memory-server-2",
            command=["npx", "-y", "@modelcontextprotocol/server-memory"],
        )

        tools = client.get_tools()
        print(f"\nTotal tools from both servers: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.name}")

        # Should have tools from both servers (same tools, different prefixes internally)
        assert len(tools) > 0

        # Verify we have two servers registered
        assert len(client._servers) == 2

    finally:
        await client.disconnect_all()


# =============================================================================
# Agent MCP Integration Tests
# =============================================================================


class TestAgentMCPIntegration:
    """Tests for Agent MCP integration."""

    @pytest.mark.asyncio
    async def test_agent_with_mcp_servers_config(self):
        """Test Agent can be configured with mcp_servers parameter."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from minicode import Agent
        from minicode.llm.base import BaseLLM

        # Create mock LLM
        mock_llm = MagicMock(spec=BaseLLM)

        # Create agent with mcp_servers config
        agent = Agent(
            name="test-agent",
            llm=mock_llm,
            mcp_servers=[
                {"name": "test-server", "command": ["echo", "test"]},
            ],
        )

        # Verify mcp_servers config is stored
        assert agent._mcp_servers_config is not None
        assert len(agent._mcp_servers_config) == 1
        assert agent._mcp_servers_config[0]["name"] == "test-server"

        # Verify MCP client is not initialized yet
        assert agent._mcp_client is None

    @pytest.mark.asyncio
    async def test_agent_initialize_mcp_validation(self):
        """Test Agent.initialize_mcp validates server config."""
        from unittest.mock import MagicMock

        from minicode import Agent
        from minicode.llm.base import BaseLLM

        mock_llm = MagicMock(spec=BaseLLM)

        # Config without 'name' should raise error
        agent = Agent(
            name="test-agent",
            llm=mock_llm,
            mcp_servers=[{"command": ["echo", "test"]}],  # Missing 'name'
        )

        with pytest.raises(ValueError, match="must include 'name'"):
            await agent.initialize_mcp()

    @pytest.mark.asyncio
    async def test_agent_no_mcp_servers(self):
        """Test Agent without mcp_servers works normally."""
        from unittest.mock import MagicMock

        from minicode import Agent
        from minicode.llm.base import BaseLLM

        mock_llm = MagicMock(spec=BaseLLM)

        agent = Agent(
            name="test-agent",
            llm=mock_llm,
        )

        # initialize_mcp should be no-op when no servers configured
        await agent.initialize_mcp()
        assert agent._mcp_client is None

        # cleanup_mcp should also be no-op
        await agent.cleanup_mcp()

    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_agent_with_real_mcp_server(self):
        """Test Agent with real MCP server using context manager.

        To run this test:
            pytest tests/test_mcp.py::TestAgentMCPIntegration::test_agent_with_real_mcp_server -v -s
        """
        if not _check_npx_available():
            pytest.skip("npx not available - install Node.js to run this test")

        from unittest.mock import MagicMock

        from minicode import Agent
        from minicode.llm.base import BaseLLM

        mock_llm = MagicMock(spec=BaseLLM)

        mcp_servers = [
            {
                "name": "memory",
                "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
            },
        ]

        async with Agent(
            name="mcp-test-agent",
            llm=mock_llm,
            mcp_servers=mcp_servers,
        ) as agent:
            # Verify MCP client was initialized
            assert agent._mcp_client is not None

            # Verify tools were registered
            tool_count = len(agent.tool_registry)
            print(f"\nRegistered {tool_count} tools from MCP server")
            assert tool_count > 0

            # Verify specific tools exist
            tool_names = agent.tool_registry.list_tools()
            assert "read_graph" in tool_names

        # After context exit, MCP client should be cleaned up
        assert agent._mcp_client is None
