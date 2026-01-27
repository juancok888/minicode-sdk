"""Bash command execution tool for minicode SDK."""

import asyncio
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool
from minicode.tools.builtin.process_manager import ProcessManager


class BashTool(BaseTool):
    """Execute bash commands in a shell session.

    This tool allows agents to run shell commands with optional timeout.
    Use for terminal operations like git, npm, docker, etc.
    """

    def __init__(
        self,
        working_directory: Optional[str] = None,
        default_timeout: int = 120000,
    ):
        """Initialize Bash tool.

        Args:
            working_directory: Default working directory for commands.
                             If None, uses current working directory.
            default_timeout: Default timeout in milliseconds (default: 120000 = 2 minutes)
        """
        self._working_directory = working_directory or str(Path.cwd())
        self._default_timeout = default_timeout
        self._process_manager = ProcessManager()

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "bash"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return """Execute bash commands in a persistent shell session with optional timeout.

Usage notes:
- Used for terminal operations like git, npm, docker, etc.
- File operations should use specialized tools (Read, Write, Edit)
- Commands timeout after the specified duration (default 2 minutes, max 10 minutes)
- Output is captured from both stdout and stderr
- Returns exit code and full command output
- Can run commands in background with run_in_background=True
- Background commands don't block, use BashOutput to monitor output
- Use KillShell to terminate background commands

Example commands:
- git status
- npm install
- python script.py
- ls -la"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute",
                },
                "description": {
                    "type": "string",
                    "description": "Clear, concise description of what this command does (5-10 words)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Optional timeout in milliseconds (max 600000 = 10 minutes)",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory to run the command in",
                },
                "run_in_background": {
                    "type": "boolean",
                    "description": "Set to true to run this command in the background (default: false)",
                    "default": False,
                },
            },
            "required": ["command"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute a bash command.

        Args:
            params: Command parameters including:
                - command: The bash command to execute
                - description: Optional description of the command
                - timeout: Optional timeout in milliseconds
                - cwd: Optional working directory
                - run_in_background: Whether to run in background
            context: Tool execution context

        Returns:
            Dictionary containing:
                - success: Whether command executed successfully
                - output: Combined stdout and stderr output (foreground only)
                - exit_code: Command exit code (foreground only)
                - timed_out: Whether command timed out (foreground only)
                - bash_id: Process ID (background only)
                - command: The executed command
        """
        command = params.get("command")
        if not command:
            return {
                "success": False,
                "error": "command parameter is required",
            }

        description = params.get("description", command[:50])
        timeout_ms = params.get("timeout", self._default_timeout)
        cwd = params.get("cwd", self._working_directory)
        run_in_background = params.get("run_in_background", False)

        # If running in background, delegate to process manager
        if run_in_background:
            result = await self._process_manager.start_process(
                command=command,
                description=description,
                cwd=cwd,
            )
            if result["success"]:
                return {
                    "success": True,
                    "bash_id": result["process_id"],
                    "command": command,
                    "description": description,
                    "message": f"Started background process {result['process_id']}. Use BashOutput to monitor output.",
                }
            else:
                return result

        # Foreground execution with timeout
        # Validate timeout
        max_timeout = 600000  # 10 minutes
        if timeout_ms > max_timeout:
            timeout_ms = max_timeout

        timeout_seconds = timeout_ms / 1000.0

        try:
            # Execute command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds,
                )
                timed_out = False
            except asyncio.TimeoutError:
                # Kill process on timeout
                process.kill()
                await process.wait()
                timed_out = True
                stdout, stderr = b"", b""

            # Decode output
            output_text = ""
            if stdout:
                output_text += stdout.decode("utf-8", errors="replace")
            if stderr:
                if output_text:
                    output_text += "\n"
                output_text += stderr.decode("utf-8", errors="replace")

            if timed_out:
                output_text += f"\n\n[Command timed out after {timeout_seconds}s]"

            exit_code = process.returncode if process.returncode is not None else -1

            return {
                "success": not timed_out and exit_code == 0,
                "output": output_text,
                "exit_code": exit_code,
                "timed_out": timed_out,
                "command": command,
                "description": description,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute command: {str(e)}",
                "command": command,
            }
