"""Tests for NotebookEdit tool."""

import json
import tempfile
from pathlib import Path

import pytest

from minicode.session.message import ToolContext
from minicode.tools.builtin import NotebookEditTool


@pytest.fixture
def tool_context():
    """Create a tool context for testing."""
    return ToolContext(agent_name="test", session_id="test-session")


@pytest.fixture
def sample_notebook(tmp_path):
    """Create a sample Jupyter notebook for testing."""
    notebook = {
        "cells": [
            {
                "id": "cell-1",
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# Test Notebook\n", "This is a test notebook."],
            },
            {
                "id": "cell-2",
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [{"data": {"text/plain": ["3"]}, "execution_count": 1, "output_type": "execute_result"}],
                "source": ["x = 1\n", "y = 2\n", "x + y"],
            },
            {
                "id": "cell-3",
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": ["print('Hello, World!')"],
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    nb_path = tmp_path / "test.ipynb"
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=1)

    return nb_path


# Basic functionality tests


@pytest.mark.asyncio
async def test_replace_cell_content(sample_notebook, tool_context):
    """Test replacing cell content."""
    tool = NotebookEditTool()

    result = await tool.execute(
        {
            "notebook_path": str(sample_notebook),
            "cell_id": "cell-2",
            "new_source": "a = 10\nb = 20\na + b",
        },
        tool_context,
    )

    assert result["success"] is True
    assert "Replaced cell cell-2" in result["message"]
    assert result["cells_count"] == 3

    # Verify the change
    with open(sample_notebook, "r") as f:
        notebook = json.load(f)

    cell = next(c for c in notebook["cells"] if c["id"] == "cell-2")
    assert cell["source"] == ["a = 10\n", "b = 20\n", "a + b"]
    assert cell["outputs"] == []  # Outputs should be cleared
    assert cell["execution_count"] is None


@pytest.mark.asyncio
async def test_replace_cell_change_type(sample_notebook, tool_context):
    """Test replacing cell and changing its type."""
    tool = NotebookEditTool()

    result = await tool.execute(
        {
            "notebook_path": str(sample_notebook),
            "cell_id": "cell-2",
            "cell_type": "markdown",
            "new_source": "## This is now markdown",
        },
        tool_context,
    )

    assert result["success"] is True

    # Verify type changed
    with open(sample_notebook, "r") as f:
        notebook = json.load(f)

    cell = next(c for c in notebook["cells"] if c["id"] == "cell-2")
    assert cell["cell_type"] == "markdown"
    assert cell["source"] == ["## This is now markdown"]


@pytest.mark.asyncio
async def test_insert_cell_after(sample_notebook, tool_context):
    """Test inserting a new cell after an existing cell."""
    tool = NotebookEditTool()

    result = await tool.execute(
        {
            "notebook_path": str(sample_notebook),
            "edit_mode": "insert",
            "cell_id": "cell-1",
            "cell_type": "code",
            "new_source": "z = 100",
        },
        tool_context,
    )

    assert result["success"] is True
    assert "Inserted new code cell" in result["message"]
    assert result["cells_count"] == 4

    # Verify insertion
    with open(sample_notebook, "r") as f:
        notebook = json.load(f)

    assert len(notebook["cells"]) == 4
    # New cell should be at index 1 (after cell-1)
    new_cell = notebook["cells"][1]
    assert new_cell["cell_type"] == "code"
    assert new_cell["source"] == ["z = 100"]
    assert "id" in new_cell


@pytest.mark.asyncio
async def test_insert_cell_at_beginning(sample_notebook, tool_context):
    """Test inserting a cell at the beginning."""
    tool = NotebookEditTool()

    result = await tool.execute(
        {
            "notebook_path": str(sample_notebook),
            "edit_mode": "insert",
            "cell_id": None,  # Insert at beginning
            "cell_type": "markdown",
            "new_source": "# New First Cell",
        },
        tool_context,
    )

    assert result["success"] is True
    assert result["cells_count"] == 4

    # Verify insertion at beginning
    with open(sample_notebook, "r") as f:
        notebook = json.load(f)

    assert notebook["cells"][0]["source"] == ["# New First Cell"]
    assert notebook["cells"][0]["cell_type"] == "markdown"


@pytest.mark.asyncio
async def test_delete_cell(sample_notebook, tool_context):
    """Test deleting a cell."""
    tool = NotebookEditTool()

    result = await tool.execute(
        {
            "notebook_path": str(sample_notebook),
            "edit_mode": "delete",
            "cell_id": "cell-2",
            "new_source": "",  # Required but not used for delete
        },
        tool_context,
    )

    assert result["success"] is True
    assert "Deleted code cell cell-2" in result["message"]
    assert result["cells_count"] == 2

    # Verify deletion
    with open(sample_notebook, "r") as f:
        notebook = json.load(f)

    assert len(notebook["cells"]) == 2
    assert not any(c["id"] == "cell-2" for c in notebook["cells"])


# Error handling tests


@pytest.mark.asyncio
async def test_missing_notebook_path(tool_context):
    """Test error when notebook_path is missing."""
    tool = NotebookEditTool()

    result = await tool.execute(
        {"new_source": "test"},
        tool_context,
    )

    assert result["success"] is False
    assert "required" in result["error"].lower()


@pytest.mark.asyncio
async def test_relative_path_error(tmp_path, tool_context):
    """Test error for relative paths."""
    tool = NotebookEditTool()

    result = await tool.execute(
        {
            "notebook_path": "relative/path.ipynb",
            "new_source": "test",
        },
        tool_context,
    )

    assert result["success"] is False
    assert "absolute path" in result["error"].lower()


@pytest.mark.asyncio
async def test_nonexistent_file(tmp_path, tool_context):
    """Test error for nonexistent file."""
    tool = NotebookEditTool()

    result = await tool.execute(
        {
            "notebook_path": str(tmp_path / "nonexistent.ipynb"),
            "new_source": "test",
        },
        tool_context,
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_wrong_extension(tmp_path, tool_context):
    """Test error for wrong file extension."""
    tool = NotebookEditTool()

    wrong_file = tmp_path / "test.txt"
    wrong_file.write_text("test")

    result = await tool.execute(
        {
            "notebook_path": str(wrong_file),
            "new_source": "test",
        },
        tool_context,
    )

    assert result["success"] is False
    assert ".ipynb" in result["error"].lower()


@pytest.mark.asyncio
async def test_invalid_json(tmp_path, tool_context):
    """Test error for invalid JSON."""
    tool = NotebookEditTool()

    invalid_nb = tmp_path / "invalid.ipynb"
    invalid_nb.write_text("not valid json")

    result = await tool.execute(
        {
            "notebook_path": str(invalid_nb),
            "new_source": "test",
        },
        tool_context,
    )

    assert result["success"] is False
    assert "invalid json" in result["error"].lower()


@pytest.mark.asyncio
async def test_cell_not_found(sample_notebook, tool_context):
    """Test error when cell ID not found."""
    tool = NotebookEditTool()

    result = await tool.execute(
        {
            "notebook_path": str(sample_notebook),
            "cell_id": "nonexistent-cell",
            "new_source": "test",
        },
        tool_context,
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_insert_without_cell_type(sample_notebook, tool_context):
    """Test error when inserting without cell_type."""
    tool = NotebookEditTool()

    result = await tool.execute(
        {
            "notebook_path": str(sample_notebook),
            "edit_mode": "insert",
            "cell_id": "cell-1",
            "new_source": "test",
        },
        tool_context,
    )

    assert result["success"] is False
    assert "cell_type" in result["error"].lower()
    assert "required" in result["error"].lower()


@pytest.mark.asyncio
async def test_delete_without_cell_id(sample_notebook, tool_context):
    """Test error when deleting without cell_id."""
    tool = NotebookEditTool()

    result = await tool.execute(
        {
            "notebook_path": str(sample_notebook),
            "edit_mode": "delete",
            "new_source": "",
        },
        tool_context,
    )

    assert result["success"] is False
    assert "cell_id" in result["error"].lower()
    assert "required" in result["error"].lower()


# Tool properties tests


def test_notebook_tool_properties():
    """Test NotebookEditTool properties."""
    tool = NotebookEditTool()

    assert tool.name == "notebook_edit"
    assert len(tool.description) > 0
    assert "notebook_path" in tool.parameters_schema["properties"]
    assert "new_source" in tool.parameters_schema["properties"]
    assert "cell_id" in tool.parameters_schema["properties"]
    assert "cell_type" in tool.parameters_schema["properties"]
    assert "edit_mode" in tool.parameters_schema["properties"]


# Edge cases


@pytest.mark.asyncio
async def test_multiline_source(sample_notebook, tool_context):
    """Test replacing with multi-line source."""
    tool = NotebookEditTool()

    multiline_source = """import numpy as np
import pandas as pd

df = pd.DataFrame({'a': [1, 2, 3]})
print(df)"""

    result = await tool.execute(
        {
            "notebook_path": str(sample_notebook),
            "cell_id": "cell-3",
            "new_source": multiline_source,
        },
        tool_context,
    )

    assert result["success"] is True

    # Verify multiline handling
    with open(sample_notebook, "r") as f:
        notebook = json.load(f)

    cell = next(c for c in notebook["cells"] if c["id"] == "cell-3")
    # Should be split into lines with newlines
    assert len(cell["source"]) == 5  # 5 lines
    assert cell["source"][0] == "import numpy as np\n"
    assert cell["source"][4] == "print(df)"  # Last line without newline


@pytest.mark.asyncio
async def test_empty_source(sample_notebook, tool_context):
    """Test replacing with empty source."""
    tool = NotebookEditTool()

    result = await tool.execute(
        {
            "notebook_path": str(sample_notebook),
            "cell_id": "cell-3",
            "new_source": "",
        },
        tool_context,
    )

    assert result["success"] is True

    with open(sample_notebook, "r") as f:
        notebook = json.load(f)

    cell = next(c for c in notebook["cells"] if c["id"] == "cell-3")
    assert cell["source"] == [""]
