"""Built-in write file tool."""

from pathlib import Path
from typing import Any, Dict

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool


class WriteTool(BaseTool):
    """Tool for writing content to files.

    This tool allows the agent to create or overwrite files.

    Note: For production use, consider adding:
    - Content size limits (e.g., MAX_CONTENT_SIZE = 10 * 1024 * 1024)
    - Path validation to restrict write locations
    - Access control and sandboxing
    """

    MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10 MB default limit

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "write_file"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return (
            "Write content to a file. "
            "Provide the file path and content as parameters. "
            "Creates parent directories if they don't exist. "
            "Overwrites existing files."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write (absolute or relative)",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8",
                },
                "create_dirs": {
                    "type": "boolean",
                    "description": "Create parent directories if they don't exist (default: true)",
                    "default": True,
                },
            },
            "required": ["path", "content"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute the write file operation."""
        path = params.get("path")
        content = params.get("content")
        encoding = params.get("encoding", "utf-8")
        create_dirs = params.get("create_dirs", True)

        if not path:
            return {
                "success": False,
                "error": "Path parameter is required",
            }

        if content is None:
            return {
                "success": False,
                "error": "Content parameter is required",
            }

        # Check content size
        if len(content) > self.MAX_CONTENT_SIZE:
            return {
                "success": False,
                "error": f"Content too large: {len(content)} bytes (max: {self.MAX_CONTENT_SIZE})",
            }

        try:
            # Convert to Path object for better path handling
            file_path = Path(path).expanduser().resolve()

            # Create parent directories if needed
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)

            return {
                "success": True,
                "data": f"Successfully wrote {len(content)} characters to {path}",
                "path": str(file_path),
                "size": len(content),
            }

        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied: {path}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write file: {str(e)}",
            }

    def requires_confirmation(self, params: Dict[str, Any]) -> bool:
        """Writing files requires confirmation."""
        return True

    def get_confirmation_message(self, params: Dict[str, Any]) -> str:
        """Get confirmation message."""
        path = params.get("path", "unknown")
        content_len = len(params.get("content", ""))
        return f"Write {content_len} characters to file: {path}?"
