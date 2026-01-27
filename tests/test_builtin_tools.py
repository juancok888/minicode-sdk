"""Tests for built-in tools (Bash, Glob, Grep, Edit)."""

import os
import tempfile
from pathlib import Path

import pytest

from minicode.session.message import ToolContext
from minicode.tools.builtin import BashTool, EditTool, GlobTool, GrepTool


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample files for testing."""
    # Create Python file
    py_file = temp_dir / "test.py"
    py_file.write_text(
        """def hello():
    print("Hello, World!")

def goodbye():
    print("Goodbye!")

# TODO: Add more functions
"""
    )

    # Create JavaScript file
    js_file = temp_dir / "test.js"
    js_file.write_text(
        """function hello() {
    console.log("Hello, World!");
}

function goodbye() {
    console.log("Goodbye!");
}
"""
    )

    # Create nested directory
    nested_dir = temp_dir / "src"
    nested_dir.mkdir()
    nested_file = nested_dir / "nested.py"
    nested_file.write_text("# Nested file\nprint('nested')")

    return {
        "py_file": py_file,
        "js_file": js_file,
        "nested_file": nested_file,
        "dir": temp_dir,
    }


@pytest.fixture
def tool_context():
    """Create a tool context for testing."""
    return ToolContext(agent_name="test", session_id="test-session")


# BashTool Tests


@pytest.mark.asyncio
async def test_bash_simple_command(tool_context):
    """Test executing a simple bash command."""
    tool = BashTool()
    result = await tool.execute(
        {"command": "echo 'Hello, World!'"},
        tool_context,
    )

    assert result["success"] is True
    assert "Hello, World!" in result["output"]
    assert result["exit_code"] == 0
    assert result["timed_out"] is False


@pytest.mark.asyncio
async def test_bash_command_with_error(tool_context):
    """Test executing a command that fails."""
    tool = BashTool()
    result = await tool.execute(
        {"command": "exit 1"},
        tool_context,
    )

    assert result["success"] is False
    assert result["exit_code"] == 1


@pytest.mark.asyncio
async def test_bash_command_timeout(tool_context):
    """Test command timeout."""
    tool = BashTool()
    result = await tool.execute(
        {"command": "sleep 5", "timeout": 100},  # 100ms timeout
        tool_context,
    )

    assert result["timed_out"] is True
    assert "timed out" in result["output"].lower()


@pytest.mark.asyncio
async def test_bash_missing_command(tool_context):
    """Test bash tool with missing command parameter."""
    tool = BashTool()
    result = await tool.execute({}, tool_context)

    assert result["success"] is False
    assert "required" in result["error"].lower()


# GlobTool Tests


@pytest.mark.asyncio
async def test_glob_find_python_files(sample_files, tool_context):
    """Test finding Python files."""
    tool = GlobTool(default_directory=str(sample_files["dir"]))
    result = await tool.execute(
        {"pattern": "**/*.py"},
        tool_context,
    )

    assert result["success"] is True
    assert result["count"] == 2
    assert any("test.py" in f for f in result["files"])
    assert any("nested.py" in f for f in result["files"])


@pytest.mark.asyncio
async def test_glob_find_js_files(sample_files, tool_context):
    """Test finding JavaScript files."""
    tool = GlobTool(default_directory=str(sample_files["dir"]))
    result = await tool.execute(
        {"pattern": "*.js"},
        tool_context,
    )

    assert result["success"] is True
    assert result["count"] == 1
    assert any("test.js" in f for f in result["files"])


@pytest.mark.asyncio
async def test_glob_no_matches(sample_files, tool_context):
    """Test glob with no matches."""
    tool = GlobTool(default_directory=str(sample_files["dir"]))
    result = await tool.execute(
        {"pattern": "*.nonexistent"},
        tool_context,
    )

    assert result["success"] is True
    assert result["count"] == 0
    assert "No files found" in result["message"]


@pytest.mark.asyncio
async def test_glob_missing_pattern(tool_context):
    """Test glob with missing pattern."""
    tool = GlobTool()
    result = await tool.execute({}, tool_context)

    assert result["success"] is False
    assert "required" in result["error"].lower()


# GrepTool Tests


@pytest.mark.asyncio
async def test_grep_find_function(sample_files, tool_context):
    """Test searching for function definitions."""
    tool = GrepTool(default_directory=str(sample_files["dir"]))
    result = await tool.execute(
        {
            "pattern": "def hello",
            "path": str(sample_files["dir"]),
        },
        tool_context,
    )

    assert result["success"] is True
    assert result["count"] > 0
    assert any("test.py" in m["file"] for m in result["matches"])


@pytest.mark.asyncio
async def test_grep_case_insensitive(sample_files, tool_context):
    """Test case-insensitive search."""
    tool = GrepTool(default_directory=str(sample_files["dir"]))
    result = await tool.execute(
        {
            "pattern": "HELLO",
            "case_insensitive": True,
        },
        tool_context,
    )

    assert result["success"] is True
    assert result["count"] > 0


@pytest.mark.asyncio
async def test_grep_with_type_filter(sample_files, tool_context):
    """Test grep with file type filter."""
    tool = GrepTool(default_directory=str(sample_files["dir"]))
    result = await tool.execute(
        {
            "pattern": "hello",
            "type": "py",
        },
        tool_context,
    )

    assert result["success"] is True
    # Should only find matches in Python files
    for match in result["matches"]:
        assert match["file"].endswith(".py")


@pytest.mark.asyncio
async def test_grep_no_matches(sample_files, tool_context):
    """Test grep with no matches."""
    tool = GrepTool(default_directory=str(sample_files["dir"]))
    result = await tool.execute(
        {"pattern": "nonexistentpattern12345"},
        tool_context,
    )

    assert result["success"] is True
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_grep_files_mode(sample_files, tool_context):
    """Test grep in files-only mode."""
    tool = GrepTool(default_directory=str(sample_files["dir"]))
    result = await tool.execute(
        {
            "pattern": "hello",
            "output_mode": "files",
        },
        tool_context,
    )

    assert result["success"] is True
    if result["count"] > 0:
        # Should return file paths only
        assert "file" in result["matches"][0]
        assert "line" not in result["matches"][0]


# EditTool Tests


@pytest.mark.asyncio
async def test_edit_simple_replacement(sample_files, tool_context):
    """Test simple string replacement."""
    tool = EditTool()
    file_path = str(sample_files["py_file"])

    result = await tool.execute(
        {
            "file_path": file_path,
            "old_string": 'print("Hello, World!")',
            "new_string": 'print("Hi there!")',
        },
        tool_context,
    )

    assert result["success"] is True
    assert result["replacements"] == 1

    # Verify file content
    content = sample_files["py_file"].read_text()
    assert 'print("Hi there!")' in content
    assert 'print("Hello, World!")' not in content


@pytest.mark.asyncio
async def test_edit_replace_all(sample_files, tool_context):
    """Test replacing all occurrences."""
    tool = EditTool()
    file_path = str(sample_files["py_file"])

    result = await tool.execute(
        {
            "file_path": file_path,
            "old_string": "print",
            "new_string": "console.log",
            "replace_all": True,
        },
        tool_context,
    )

    assert result["success"] is True
    assert result["replacements"] == 2  # Two print statements

    # Verify file content
    content = sample_files["py_file"].read_text()
    assert "console.log" in content
    assert "print" not in content


@pytest.mark.asyncio
async def test_edit_string_not_found(sample_files, tool_context):
    """Test edit with string not found."""
    tool = EditTool()
    result = await tool.execute(
        {
            "file_path": str(sample_files["py_file"]),
            "old_string": "nonexistent_string",
            "new_string": "replacement",
        },
        tool_context,
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_edit_non_unique_string(sample_files, tool_context):
    """Test edit with non-unique string without replace_all."""
    tool = EditTool()
    result = await tool.execute(
        {
            "file_path": str(sample_files["py_file"]),
            "old_string": "def",  # Appears twice
            "new_string": "function",
        },
        tool_context,
    )

    assert result["success"] is False
    assert "appears" in result["error"].lower()
    assert "replace_all" in result["error"].lower()


@pytest.mark.asyncio
async def test_edit_same_strings(sample_files, tool_context):
    """Test edit with identical old and new strings."""
    tool = EditTool()
    result = await tool.execute(
        {
            "file_path": str(sample_files["py_file"]),
            "old_string": "hello",
            "new_string": "hello",
        },
        tool_context,
    )

    assert result["success"] is False
    assert "must be different" in result["error"].lower()


@pytest.mark.asyncio
async def test_edit_nonexistent_file(tool_context):
    """Test edit with nonexistent file."""
    tool = EditTool()
    result = await tool.execute(
        {
            "file_path": "/nonexistent/file.py",
            "old_string": "old",
            "new_string": "new",
        },
        tool_context,
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


# Tool Properties Tests


def test_bash_tool_properties():
    """Test BashTool properties."""
    tool = BashTool()
    assert tool.name == "bash"
    assert len(tool.description) > 0
    assert "command" in tool.parameters_schema["properties"]


def test_glob_tool_properties():
    """Test GlobTool properties."""
    tool = GlobTool()
    assert tool.name == "glob"
    assert len(tool.description) > 0
    assert "pattern" in tool.parameters_schema["properties"]


def test_grep_tool_properties():
    """Test GrepTool properties."""
    tool = GrepTool()
    assert tool.name == "grep"
    assert len(tool.description) > 0
    assert "pattern" in tool.parameters_schema["properties"]


def test_edit_tool_properties():
    """Test EditTool properties."""
    tool = EditTool()
    assert tool.name == "edit"
    assert len(tool.description) > 0
    assert "file_path" in tool.parameters_schema["properties"]
    assert "old_string" in tool.parameters_schema["properties"]
    assert "new_string" in tool.parameters_schema["properties"]
