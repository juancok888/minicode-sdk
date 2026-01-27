"""Glob file pattern matching tool for minicode SDK."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool


class GlobTool(BaseTool):
    """Fast file pattern matching tool using glob patterns.

    Supports any codebase size and returns files sorted by modification time.
    """

    def __init__(self, default_directory: Optional[str] = None):
        """Initialize Glob tool.

        Args:
            default_directory: Default directory to search in.
                             If None, uses current working directory.
        """
        self._default_directory = default_directory or str(Path.cwd())

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "glob"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return """Fast file pattern matching tool that works with any codebase size.

Supports glob patterns like:
- **/*.js - All JavaScript files recursively
- src/**/*.ts - All TypeScript files in src directory
- *.py - Python files in root directory
- tests/**/test_*.py - Test files in tests directory

Returns matching file paths sorted by modification time (newest first).

Usage notes:
- Use this tool to find files by name patterns
- For content search, use the Grep tool instead
- Results are limited to 100 files to avoid overwhelming output"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match files against (e.g., '**/*.py', 'src/**/*.ts')",
                },
                "path": {
                    "type": "string",
                    "description": "The directory to search in. Defaults to current working directory.",
                },
            },
            "required": ["pattern"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute glob pattern matching.

        Args:
            params: Parameters including:
                - pattern: Glob pattern to match
                - path: Optional directory to search in
            context: Tool execution context

        Returns:
            Dictionary containing:
                - success: Whether operation succeeded
                - files: List of matching file paths
                - count: Number of files found
                - truncated: Whether results were truncated
        """
        pattern = params.get("pattern")
        if not pattern:
            return {
                "success": False,
                "error": "pattern parameter is required",
            }

        search_path = params.get("path", self._default_directory)

        # Convert to absolute path
        if not os.path.isabs(search_path):
            search_path = os.path.abspath(search_path)

        try:
            # Check if directory exists
            if not os.path.isdir(search_path):
                return {
                    "success": False,
                    "error": f"Directory not found: {search_path}",
                }

            # Find matching files
            matches: List[tuple[Path, float]] = []
            search_dir = Path(search_path)

            for file_path in search_dir.glob(pattern):
                if file_path.is_file():
                    try:
                        mtime = file_path.stat().st_mtime
                        matches.append((file_path, mtime))
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue

            # Sort by modification time (newest first)
            matches.sort(key=lambda x: x[1], reverse=True)

            # Limit results to 100 files
            limit = 100
            truncated = len(matches) > limit
            matches = matches[:limit]

            # Convert to list of path strings
            file_paths = [str(path) for path, _ in matches]

            if len(file_paths) == 0:
                message = "No files found"
            else:
                message = f"Found {len(file_paths)} file(s)"
                if truncated:
                    message += " (truncated to 100 files)"

            return {
                "success": True,
                "files": file_paths,
                "count": len(file_paths),
                "truncated": truncated,
                "message": message,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Glob search failed: {str(e)}",
            }
