"""Background process manager for bash shells."""

import asyncio
import uuid
from typing import Any, Dict, Optional


class BackgroundProcess:
    """Represents a background shell process."""

    def __init__(
        self,
        process_id: str,
        process: asyncio.subprocess.Process,
        command: str,
        description: str,
    ):
        """Initialize background process.

        Args:
            process_id: Unique identifier for the process
            process: The subprocess.Process object
            command: The command being executed
            description: Description of the command
        """
        self.process_id = process_id
        self.process = process
        self.command = command
        self.description = description
        self.output_buffer: list[str] = []
        self._lock = asyncio.Lock()
        self._reader_task: Optional[asyncio.Task] = None
        self._start_output_reader()

    def _start_output_reader(self) -> None:
        """Start background task to read process output."""
        self._reader_task = asyncio.create_task(self._read_output())

    async def _read_output(self) -> None:
        """Continuously read output from the process."""
        try:
            while True:
                # Read from stdout
                if self.process.stdout:
                    try:
                        line = await asyncio.wait_for(
                            self.process.stdout.readline(),
                            timeout=0.1,
                        )
                        if line:
                            async with self._lock:
                                self.output_buffer.append(
                                    line.decode("utf-8", errors="replace")
                                )
                    except asyncio.TimeoutError:
                        pass

                # Check if process is still running
                if self.process.returncode is not None:
                    break

                await asyncio.sleep(0.1)

        except Exception:
            # Process might have been killed
            pass

    async def get_new_output(self) -> str:
        """Get new output since last call.

        Returns:
            New output as string
        """
        async with self._lock:
            output = "".join(self.output_buffer)
            self.output_buffer.clear()
            return output

    async def kill(self) -> Dict[str, Any]:
        """Kill the background process.

        Returns:
            Dictionary with kill result
        """
        try:
            if self.process.returncode is None:
                self.process.kill()
                await self.process.wait()
                status = "killed"
            else:
                status = "already_finished"

            # Cancel reader task
            if self._reader_task and not self._reader_task.done():
                self._reader_task.cancel()
                try:
                    await self._reader_task
                except asyncio.CancelledError:
                    pass

            return {
                "success": True,
                "status": status,
                "exit_code": self.process.returncode,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to kill process: {str(e)}",
            }

    def is_running(self) -> bool:
        """Check if process is still running.

        Returns:
            True if running, False otherwise
        """
        return self.process.returncode is None


class ProcessManager:
    """Manages background shell processes."""

    _instance: Optional["ProcessManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls) -> "ProcessManager":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._processes: Dict[str, BackgroundProcess] = {}
        return cls._instance

    async def start_process(
        self,
        command: str,
        description: str,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start a background process.

        Args:
            command: Command to execute
            description: Description of the command
            cwd: Working directory

        Returns:
            Dictionary with process info
        """
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Merge stderr into stdout
                cwd=cwd,
            )

            # Generate unique ID
            process_id = str(uuid.uuid4())

            # Create background process wrapper
            bg_process = BackgroundProcess(
                process_id=process_id,
                process=process,
                command=command,
                description=description,
            )

            # Store in registry
            async with self._lock:
                self._processes[process_id] = bg_process

            return {
                "success": True,
                "process_id": process_id,
                "command": command,
                "description": description,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to start process: {str(e)}",
            }

    async def get_process_output(
        self,
        process_id: str,
        filter_pattern: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get output from a background process.

        Args:
            process_id: Process ID
            filter_pattern: Optional regex pattern to filter output

        Returns:
            Dictionary with output
        """
        async with self._lock:
            if process_id not in self._processes:
                return {
                    "success": False,
                    "error": f"Process {process_id} not found",
                }

            process = self._processes[process_id]

        # Get new output
        output = await process.get_new_output()

        # Apply filter if provided
        if filter_pattern and output:
            import re

            try:
                pattern = re.compile(filter_pattern)
                lines = output.splitlines(keepends=True)
                filtered_lines = [line for line in lines if pattern.search(line)]
                output = "".join(filtered_lines)
            except re.error as e:
                return {
                    "success": False,
                    "error": f"Invalid filter pattern: {str(e)}",
                }

        return {
            "success": True,
            "output": output,
            "is_running": process.is_running(),
            "exit_code": process.process.returncode,
        }

    async def kill_process(self, process_id: str) -> Dict[str, Any]:
        """Kill a background process.

        Args:
            process_id: Process ID to kill

        Returns:
            Dictionary with kill result
        """
        async with self._lock:
            if process_id not in self._processes:
                return {
                    "success": False,
                    "error": f"Process {process_id} not found",
                }

            process = self._processes[process_id]

        # Kill the process
        result = await process.kill()

        # Remove from registry
        if result["success"]:
            async with self._lock:
                del self._processes[process_id]

        return result

    async def list_processes(self) -> Dict[str, Any]:
        """List all background processes.

        Returns:
            Dictionary with process list
        """
        async with self._lock:
            processes = []
            for process in self._processes.values():
                processes.append(
                    {
                        "process_id": process.process_id,
                        "command": process.command,
                        "description": process.description,
                        "is_running": process.is_running(),
                        "exit_code": process.process.returncode,
                    }
                )

        return {
            "success": True,
            "processes": processes,
            "count": len(processes),
        }

    async def cleanup_finished(self) -> None:
        """Clean up finished processes."""
        async with self._lock:
            finished = [
                pid
                for pid, proc in self._processes.items()
                if not proc.is_running()
            ]
            for pid in finished:
                del self._processes[pid]
