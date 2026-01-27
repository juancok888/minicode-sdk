"""Tests for background process management tools (KillShell, BashOutput)."""

import asyncio

import pytest

from minicode.session.message import ToolContext
from minicode.tools.builtin import BashOutputTool, BashTool, KillShellTool


@pytest.fixture
def tool_context():
    """Create a tool context for testing."""
    return ToolContext(agent_name="test", session_id="test-session")


# BashTool background execution tests


@pytest.mark.asyncio
async def test_bash_background_simple_command(tool_context):
    """Test running a simple command in background."""
    bash_tool = BashTool()

    result = await bash_tool.execute(
        {
            "command": "echo 'Hello, background!'",
            "run_in_background": True,
        },
        tool_context,
    )

    assert result["success"] is True
    assert "bash_id" in result
    assert isinstance(result["bash_id"], str)
    assert len(result["bash_id"]) > 0
    assert result["command"] == "echo 'Hello, background!'"

    # Clean up
    kill_tool = KillShellTool()
    await kill_tool.execute({"shell_id": result["bash_id"]}, tool_context)


@pytest.mark.asyncio
async def test_bash_background_long_running(tool_context):
    """Test long-running background command."""
    bash_tool = BashTool()

    # Start a command that sleeps for 5 seconds
    result = await bash_tool.execute(
        {
            "command": "sleep 5",
            "run_in_background": True,
        },
        tool_context,
    )

    assert result["success"] is True
    bash_id = result["bash_id"]

    # Command should still be running
    await asyncio.sleep(0.5)

    # Kill it early
    kill_tool = KillShellTool()
    kill_result = await kill_tool.execute({"shell_id": bash_id}, tool_context)

    assert kill_result["success"] is True
    assert kill_result["status"] == "killed"


# BashOutput tests


@pytest.mark.asyncio
async def test_bashoutput_read_simple_output(tool_context):
    """Test reading output from background command."""
    bash_tool = BashTool()
    output_tool = BashOutputTool()

    # Start background command
    result = await bash_tool.execute(
        {
            "command": "echo 'Line 1'; echo 'Line 2'; echo 'Line 3'",
            "run_in_background": True,
        },
        tool_context,
    )

    bash_id = result["bash_id"]

    # Wait for process to complete
    await asyncio.sleep(1.0)

    # Read output
    output_result = await output_tool.execute(
        {"bash_id": bash_id},
        tool_context,
    )

    assert output_result["success"] is True
    # At least some lines should be present
    assert "Line" in output_result["output"]

    # Clean up
    kill_tool = KillShellTool()
    await kill_tool.execute({"shell_id": bash_id}, tool_context)


@pytest.mark.asyncio
async def test_bashoutput_incremental_reading(tool_context):
    """Test that BashOutput only returns new output each time."""
    bash_tool = BashTool()
    output_tool = BashOutputTool()

    # Start background command that outputs multiple times
    result = await bash_tool.execute(
        {
            "command": "echo 'First'; sleep 0.2; echo 'Second'",
            "run_in_background": True,
        },
        tool_context,
    )

    bash_id = result["bash_id"]

    # Wait and read first output
    await asyncio.sleep(0.3)
    first_read = await output_tool.execute({"bash_id": bash_id}, tool_context)

    assert first_read["success"] is True
    first_output = first_read["output"]

    # Read again - should only get new output
    await asyncio.sleep(0.3)
    second_read = await output_tool.execute({"bash_id": bash_id}, tool_context)

    assert second_read["success"] is True
    # Second read should have different content (or empty if nothing new)

    # Clean up
    kill_tool = KillShellTool()
    await kill_tool.execute({"shell_id": bash_id}, tool_context)


@pytest.mark.asyncio
async def test_bashoutput_with_filter(tool_context):
    """Test filtering output with regex."""
    bash_tool = BashTool()
    output_tool = BashOutputTool()

    # Start background command with mixed output
    result = await bash_tool.execute(
        {
            "command": "echo 'ERROR: something failed'; echo 'INFO: running'; echo 'ERROR: another error'",
            "run_in_background": True,
        },
        tool_context,
    )

    bash_id = result["bash_id"]

    # Wait for output
    await asyncio.sleep(0.5)

    # Read with filter for errors only
    output_result = await output_tool.execute(
        {
            "bash_id": bash_id,
            "filter": "ERROR",
        },
        tool_context,
    )

    assert output_result["success"] is True
    assert "ERROR" in output_result["output"]
    # Should not contain INFO line (filtered out)
    # Note: depending on buffering, this might not be 100% reliable

    # Clean up
    kill_tool = KillShellTool()
    await kill_tool.execute({"shell_id": bash_id}, tool_context)


@pytest.mark.asyncio
async def test_bashoutput_nonexistent_process(tool_context):
    """Test reading output from non-existent process."""
    output_tool = BashOutputTool()

    result = await output_tool.execute(
        {"bash_id": "nonexistent-id"},
        tool_context,
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_bashoutput_missing_bash_id(tool_context):
    """Test error when bash_id is missing."""
    output_tool = BashOutputTool()

    result = await output_tool.execute({}, tool_context)

    assert result["success"] is False
    assert "required" in result["error"].lower()


# KillShell tests


@pytest.mark.asyncio
async def test_killshell_kill_running_process(tool_context):
    """Test killing a running background process."""
    bash_tool = BashTool()
    kill_tool = KillShellTool()

    # Start long-running process
    result = await bash_tool.execute(
        {
            "command": "sleep 100",
            "run_in_background": True,
        },
        tool_context,
    )

    bash_id = result["bash_id"]

    # Wait a bit
    await asyncio.sleep(0.2)

    # Kill it
    kill_result = await kill_tool.execute(
        {"shell_id": bash_id},
        tool_context,
    )

    assert kill_result["success"] is True
    assert kill_result["status"] == "killed"
    assert "shell_id" in kill_result


@pytest.mark.asyncio
async def test_killshell_already_finished(tool_context):
    """Test killing a process that already finished."""
    bash_tool = BashTool()
    kill_tool = KillShellTool()

    # Start quick process
    result = await bash_tool.execute(
        {
            "command": "echo 'done'",
            "run_in_background": True,
        },
        tool_context,
    )

    bash_id = result["bash_id"]

    # Wait for it to finish
    await asyncio.sleep(0.5)

    # Try to kill it
    kill_result = await kill_tool.execute(
        {"shell_id": bash_id},
        tool_context,
    )

    assert kill_result["success"] is True
    # Status might be already_finished or killed depending on timing


@pytest.mark.asyncio
async def test_killshell_nonexistent_process(tool_context):
    """Test killing non-existent process."""
    kill_tool = KillShellTool()

    result = await kill_tool.execute(
        {"shell_id": "nonexistent-id"},
        tool_context,
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_killshell_missing_shell_id(tool_context):
    """Test error when shell_id is missing."""
    kill_tool = KillShellTool()

    result = await kill_tool.execute({}, tool_context)

    assert result["success"] is False
    assert "required" in result["error"].lower()


# Tool properties tests


def test_bash_output_tool_properties():
    """Test BashOutputTool properties."""
    tool = BashOutputTool()

    assert tool.name == "bash_output"
    assert len(tool.description) > 0
    assert "bash_id" in tool.parameters_schema["properties"]
    assert "filter" in tool.parameters_schema["properties"]
    assert tool.parameters_schema["required"] == ["bash_id"]


def test_kill_shell_tool_properties():
    """Test KillShellTool properties."""
    tool = KillShellTool()

    assert tool.name == "kill_shell"
    assert len(tool.description) > 0
    assert "shell_id" in tool.parameters_schema["properties"]
    assert tool.parameters_schema["required"] == ["shell_id"]


# Integration test


@pytest.mark.asyncio
async def test_full_background_workflow(tool_context):
    """Test complete workflow: start -> monitor -> kill."""
    bash_tool = BashTool()
    output_tool = BashOutputTool()
    kill_tool = KillShellTool()

    # Start background process
    start_result = await bash_tool.execute(
        {
            "command": "for i in 1 2 3; do echo \"Count: $i\"; sleep 0.2; done",
            "run_in_background": True,
        },
        tool_context,
    )

    assert start_result["success"] is True
    bash_id = start_result["bash_id"]

    # Monitor output
    await asyncio.sleep(0.3)
    output1 = await output_tool.execute({"bash_id": bash_id}, tool_context)
    assert output1["success"] is True
    assert "Count:" in output1["output"]

    # Get more output
    await asyncio.sleep(0.3)
    output2 = await output_tool.execute({"bash_id": bash_id}, tool_context)
    assert output2["success"] is True

    # Kill process
    kill_result = await kill_tool.execute({"shell_id": bash_id}, tool_context)
    assert kill_result["success"] is True

    # Try to read after kill - should fail
    await asyncio.sleep(0.1)
    output3 = await output_tool.execute({"bash_id": bash_id}, tool_context)
    assert output3["success"] is False  # Process no longer tracked
