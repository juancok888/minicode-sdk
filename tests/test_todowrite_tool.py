"""Tests for TodoWrite tool."""

import pytest

from minicode.session.message import ToolContext
from minicode.tools.builtin import TodoWriteTool


@pytest.fixture
def tool_context():
    """Create a tool context for testing."""
    context = ToolContext(agent_name="test", session_id="test-session")
    context.metadata = {}  # Initialize metadata dict
    return context


# Basic functionality tests


@pytest.mark.asyncio
async def test_valid_todo_list(tool_context):
    """Test creating a valid todo list."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Implement feature X",
                    "activeForm": "Implementing feature X",
                    "status": "pending",
                },
                {
                    "content": "Write tests",
                    "activeForm": "Writing tests",
                    "status": "in_progress",
                },
                {
                    "content": "Update docs",
                    "activeForm": "Updating docs",
                    "status": "completed",
                },
            ]
        },
        tool_context,
    )

    assert result["success"] is True
    assert result["total_tasks"] == 3
    assert result["status_counts"]["pending"] == 1
    assert result["status_counts"]["in_progress"] == 1
    assert result["status_counts"]["completed"] == 1
    assert "warning" not in result


@pytest.mark.asyncio
async def test_todos_stored_in_metadata(tool_context):
    """Test that todos are stored in context metadata."""
    tool = TodoWriteTool()

    todos = [
        {
            "content": "Task 1",
            "activeForm": "Doing task 1",
            "status": "pending",
        }
    ]

    await tool.execute({"todos": todos}, tool_context)

    assert "todos" in tool_context.metadata
    assert tool_context.metadata["todos"] == todos


@pytest.mark.asyncio
async def test_empty_todo_list(tool_context):
    """Test creating an empty todo list."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {"todos": []},
        tool_context,
    )

    assert result["success"] is True
    assert result["total_tasks"] == 0
    assert result["status_counts"]["pending"] == 0
    assert result["status_counts"]["in_progress"] == 0
    assert result["status_counts"]["completed"] == 0


# Validation tests


@pytest.mark.asyncio
async def test_missing_todos_parameter(tool_context):
    """Test error when todos parameter is missing."""
    tool = TodoWriteTool()

    result = await tool.execute({}, tool_context)

    assert result["success"] is False
    assert "required" in result["error"].lower()


@pytest.mark.asyncio
async def test_todos_not_a_list(tool_context):
    """Test error when todos is not a list."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {"todos": "not a list"},
        tool_context,
    )

    assert result["success"] is False
    assert "must be a list" in result["error"].lower()


@pytest.mark.asyncio
async def test_todo_not_a_dict(tool_context):
    """Test error when a todo item is not a dictionary."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {"todos": ["not a dict"]},
        tool_context,
    )

    assert result["success"] is False
    assert "must be a dictionary" in result["error"].lower()


@pytest.mark.asyncio
async def test_missing_content_field(tool_context):
    """Test error when content field is missing."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {
            "todos": [
                {
                    "activeForm": "Doing something",
                    "status": "pending",
                }
            ]
        },
        tool_context,
    )

    assert result["success"] is False
    assert "missing required field: content" in result["error"].lower()


@pytest.mark.asyncio
async def test_missing_status_field(tool_context):
    """Test error when status field is missing."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Do something",
                    "activeForm": "Doing something",
                }
            ]
        },
        tool_context,
    )

    assert result["success"] is False
    assert "missing required field: status" in result["error"].lower()


@pytest.mark.asyncio
async def test_missing_active_form_field(tool_context):
    """Test error when activeForm field is missing."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Do something",
                    "status": "pending",
                }
            ]
        },
        tool_context,
    )

    assert result["success"] is False
    assert "missing required field: activeform" in result["error"].lower()


@pytest.mark.asyncio
async def test_invalid_status(tool_context):
    """Test error when status has invalid value."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Do something",
                    "activeForm": "Doing something",
                    "status": "invalid_status",
                }
            ]
        },
        tool_context,
    )

    assert result["success"] is False
    assert "invalid status" in result["error"].lower()


@pytest.mark.asyncio
async def test_empty_content(tool_context):
    """Test error when content is empty."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "   ",
                    "activeForm": "Doing something",
                    "status": "pending",
                }
            ]
        },
        tool_context,
    )

    assert result["success"] is False
    assert "empty content" in result["error"].lower()


@pytest.mark.asyncio
async def test_empty_active_form(tool_context):
    """Test error when activeForm is empty."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Do something",
                    "activeForm": "   ",
                    "status": "pending",
                }
            ]
        },
        tool_context,
    )

    assert result["success"] is False
    assert "empty activeform" in result["error"].lower()


# Warning tests


@pytest.mark.asyncio
async def test_multiple_in_progress_warning(tool_context):
    """Test warning when multiple tasks are in_progress."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Task 1",
                    "activeForm": "Doing task 1",
                    "status": "in_progress",
                },
                {
                    "content": "Task 2",
                    "activeForm": "Doing task 2",
                    "status": "in_progress",
                },
            ]
        },
        tool_context,
    )

    assert result["success"] is True
    assert "warning" in result
    assert "2 tasks are in_progress" in result["warning"]
    assert "exactly 1" in result["warning"]


@pytest.mark.asyncio
async def test_no_in_progress_with_pending_warning(tool_context):
    """Test warning when no task is in_progress but pending tasks exist."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Task 1",
                    "activeForm": "Doing task 1",
                    "status": "pending",
                },
                {
                    "content": "Task 2",
                    "activeForm": "Doing task 2",
                    "status": "pending",
                },
            ]
        },
        tool_context,
    )

    assert result["success"] is True
    assert "warning" in result
    assert "no task is in_progress" in result["warning"].lower()


@pytest.mark.asyncio
async def test_no_warning_with_one_in_progress(tool_context):
    """Test no warning when exactly one task is in_progress."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Task 1",
                    "activeForm": "Doing task 1",
                    "status": "pending",
                },
                {
                    "content": "Task 2",
                    "activeForm": "Doing task 2",
                    "status": "in_progress",
                },
                {
                    "content": "Task 3",
                    "activeForm": "Doing task 3",
                    "status": "completed",
                },
            ]
        },
        tool_context,
    )

    assert result["success"] is True
    assert "warning" not in result


@pytest.mark.asyncio
async def test_no_warning_all_completed(tool_context):
    """Test no warning when all tasks are completed."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Task 1",
                    "activeForm": "Doing task 1",
                    "status": "completed",
                },
                {
                    "content": "Task 2",
                    "activeForm": "Doing task 2",
                    "status": "completed",
                },
            ]
        },
        tool_context,
    )

    assert result["success"] is True
    assert "warning" not in result


# Tool properties tests


def test_todowrite_tool_properties():
    """Test TodoWriteTool properties."""
    tool = TodoWriteTool()

    assert tool.name == "todo_write"
    assert len(tool.description) > 0
    assert "todos" in tool.parameters_schema["properties"]
    assert tool.parameters_schema["properties"]["todos"]["type"] == "array"

    # Check todo item schema
    item_schema = tool.parameters_schema["properties"]["todos"]["items"]
    assert "content" in item_schema["properties"]
    assert "activeForm" in item_schema["properties"]
    assert "status" in item_schema["properties"]
    assert item_schema["required"] == ["content", "status", "activeForm"]


# Edge cases


@pytest.mark.asyncio
async def test_very_long_content(tool_context):
    """Test with very long content strings."""
    tool = TodoWriteTool()

    long_content = "A" * 1000
    long_active = "B" * 1000

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": long_content,
                    "activeForm": long_active,
                    "status": "pending",
                }
            ]
        },
        tool_context,
    )

    assert result["success"] is True
    assert tool_context.metadata["todos"][0]["content"] == long_content


@pytest.mark.asyncio
async def test_special_characters_in_content(tool_context):
    """Test with special characters in content."""
    tool = TodoWriteTool()

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Fix bug #123: Handle 'quotes' & <tags>",
                    "activeForm": "Fixing bug #123",
                    "status": "pending",
                }
            ]
        },
        tool_context,
    )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_large_todo_list(tool_context):
    """Test with a large number of todos."""
    tool = TodoWriteTool()

    todos = [
        {
            "content": f"Task {i}",
            "activeForm": f"Doing task {i}",
            "status": "pending",
        }
        for i in range(100)
    ]

    result = await tool.execute({"todos": todos}, tool_context)

    assert result["success"] is True
    assert result["total_tasks"] == 100
    assert result["status_counts"]["pending"] == 100
