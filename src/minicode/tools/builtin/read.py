"""Built-in read file tool."""

import os
from pathlib import Path
from typing import Any, Dict

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool


class ReadTool(BaseTool):
    """Tool for reading file contents.

    This tool allows the agent to read files from the filesystem.

    Note: For production use, consider adding:
    - File size limits (e.g., MAX_FILE_SIZE = 10 * 1024 * 1024)
    - Path validation/sanitization
    - Access control based on allowed directories
    """

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB default limit

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "read_file"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return (
            "Read the contents of a file. "
            "Provide the file path as a parameter. "
            "Returns the file contents as text."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read (absolute or relative)",
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8",
                },
            },
            "required": ["path"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute the read file operation."""
        path = params.get("path")
        encoding = params.get("encoding", "utf-8")

        if not path:
            return {
                "success": False,
                "error": "Path parameter is required",
            }

        try:
            # Convert to Path object for better path handling
            file_path = Path(path).expanduser().resolve()

            # Check if file exists
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}",
                }

            # Check if it's a file (not a directory)
            if not file_path.is_file():
                return {
                    "success": False,
                    "error": f"Not a file: {path}",
                }

            # Check file size (prevent reading very large files)
            file_size = file_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                return {
                    "success": False,
                    "error": f"File too large: {file_size} bytes (max: {self.MAX_FILE_SIZE})",
                }

            # Read the file
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()

            return {
                "success": True,
                "data": content,
                "path": str(file_path),
                "size": len(content),
            }

        except UnicodeDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to decode file with encoding '{encoding}': {str(e)}",
            }
        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied: {path}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {str(e)}",
            }
