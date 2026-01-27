"""BashOutput tool for retrieving output from background bash shells."""

from typing import Any, Dict, Optional

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool
from minicode.tools.builtin.process_manager import ProcessManager


class BashOutputTool(BaseTool):
    """Tool for retrieving output from background bash shells.

    This tool reads output from background processes started by BashTool
    with run_in_background=True.
    """

    def __init__(self):
        """Initialize BashOutput tool."""
        self._process_manager = ProcessManager()

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "bash_output"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return """Retrieves output from a running or completed background bash shell.

Usage notes:
- Takes a bash_id parameter identifying the shell
- Always returns only new output since the last check
- Returns stdout and stderr output along with shell status
- Supports optional regex filtering to show only matching lines
- Use this tool when you need to monitor or check long-running shells
- Shell IDs can be found using the /tasks command

Example:
- bash_id: "abc123-def456-789" (the ID returned when starting background shell)
- filter: "error|warning" (optional regex to filter output lines)"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "bash_id": {
                    "type": "string",
                    "description": "The ID of the background shell to retrieve output from",
                },
                "filter": {
                    "type": "string",
                    "description": "Optional regular expression to filter output lines. Only matching lines will be included.",
                },
            },
            "required": ["bash_id"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute output retrieval.

        Args:
            params: Parameters including:
                - bash_id: The ID of the shell to read output from
                - filter: Optional regex pattern to filter output
            context: Tool execution context

        Returns:
            Dictionary containing:
                - success: Whether retrieval succeeded
                - output: New output since last check
                - is_running: Whether process is still running
                - exit_code: Exit code if process finished
                - error: Error message if failed
        """
        bash_id = params.get("bash_id")
        if not bash_id:
            return {
                "success": False,
                "error": "bash_id parameter is required",
            }

        filter_pattern: Optional[str] = params.get("filter")

        # Get process output
        result = await self._process_manager.get_process_output(bash_id, filter_pattern)

        if result["success"]:
            output = result.get("output", "")
            is_running = result.get("is_running", False)
            exit_code = result.get("exit_code")

            status = "running" if is_running else "finished"
            if not is_running and exit_code is not None:
                status += f" (exit code: {exit_code})"

            return {
                "success": True,
                "output": output,
                "is_running": is_running,
                "exit_code": exit_code,
                "status": status,
                "bash_id": bash_id,
            }
        else:
            return result
