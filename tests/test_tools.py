"""Tests for tool system."""

import pytest

from minicode.session.message import ToolContext
from minicode.tools import BaseTool, ToolRegistry
from minicode.tools.builtin import ReadTool, WriteTool


class MockTool(BaseTool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool"

    @property
    def parameters_schema(self):
        return {"type": "object", "properties": {}}

    async def execute(self, params, context):
        return {"success": True, "data": "mock result"}


def test_tool_registry():
    """Test tool registry operations."""
    registry = ToolRegistry()
    tool = MockTool()

    # Register tool
    registry.register(tool)
    assert registry.has("mock_tool")
    assert len(registry) == 1

    # Get tool
    retrieved = registry.get("mock_tool")
    assert retrieved is tool

    # List tools
    tools = registry.list_tools()
    assert "mock_tool" in tools

    # Unregister
    registry.unregister("mock_tool")
    assert not registry.has("mock_tool")


def test_tool_registry_duplicate():
    """Test that registering duplicate tools raises error."""
    registry = ToolRegistry()
    tool = MockTool()

    registry.register(tool)

    with pytest.raises(ValueError):
        registry.register(tool)


def test_read_tool():
    """Test ReadTool properties."""
    tool = ReadTool()
    assert tool.name == "read_file"
    assert "read" in tool.description.lower()
    assert "path" in tool.parameters_schema["properties"]


def test_write_tool():
    """Test WriteTool properties."""
    tool = WriteTool()
    assert tool.name == "write_file"
    assert "write" in tool.description.lower()
    assert "path" in tool.parameters_schema["properties"]
    assert "content" in tool.parameters_schema["properties"]


def test_tool_requires_confirmation():
    """Test tool confirmation logic."""
    read_tool = ReadTool()
    write_tool = WriteTool()

    assert not read_tool.requires_confirmation({})
    assert write_tool.requires_confirmation({})


def test_tool_to_openai_format():
    """Test converting tool to OpenAI format."""
    tool = MockTool()
    openai_format = tool.to_openai_format()

    assert openai_format["type"] == "function"
    assert openai_format["function"]["name"] == "mock_tool"
    assert openai_format["function"]["description"] == "A mock tool"
