"""KillShell tool for terminating background bash shells."""

from typing import Any, Dict

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool
from minicode.tools.builtin.process_manager import ProcessManager


class KillShellTool(BaseTool):
    """Tool for killing background bash shell processes.

    This tool terminates background processes started by BashTool with
    run_in_background=True.
    """

    def __init__(self):
        """Initialize KillShell tool."""
        self._process_manager = ProcessManager()

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "kill_shell"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return """Kills a running background bash shell by its ID.

Usage notes:
- Takes a shell_id parameter identifying the shell to kill
- Returns success or failure status
- Use this tool when you need to terminate a long-running shell
- Shell IDs can be found using the /tasks command or BashOutput tool

Example:
- shell_id: "abc123-def456-789" (the ID returned when starting background shell)"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "shell_id": {
                    "type": "string",
                    "description": "The ID of the background shell to kill",
                },
            },
            "required": ["shell_id"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute shell kill operation.

        Args:
            params: Parameters including:
                - shell_id: The ID of the shell to kill
            context: Tool execution context

        Returns:
            Dictionary containing:
                - success: Whether kill succeeded
                - status: Status of the process (killed/already_finished)
                - exit_code: Exit code if process finished
                - error: Error message if failed
        """
        shell_id = params.get("shell_id")
        if not shell_id:
            return {
                "success": False,
                "error": "shell_id parameter is required",
            }

        # Kill the process
        result = await self._process_manager.kill_process(shell_id)

        if result["success"]:
            status = result.get("status", "killed")
            exit_code = result.get("exit_code")

            message = f"Shell {shell_id} {status}"
            if exit_code is not None:
                message += f" (exit code: {exit_code})"

            return {
                "success": True,
                "message": message,
                "shell_id": shell_id,
                "status": status,
                "exit_code": exit_code,
            }
        else:
            return result
