"""Edit tool for precise string replacement in files."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool


class EditTool(BaseTool):
    """Perform precise string replacements in files.

    This tool replaces exact string matches in files. Must read file first
    to ensure you have the correct content to replace.
    """

    def __init__(self, default_directory: Optional[str] = None):
        """Initialize Edit tool.

        Args:
            default_directory: Default directory for relative paths.
                             If None, uses current working directory.
        """
        self._default_directory = default_directory or str(Path.cwd())
        self._read_files: Dict[str, str] = {}  # Track files read in session

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "edit"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return """Perform precise string replacements in files.

Usage notes:
- You MUST use the Read tool first before editing a file
- The old_string must match exactly (including whitespace and indentation)
- When copying from Read output, preserve exact formatting after line number prefix
- The edit will FAIL if old_string is not unique unless replace_all=true
- Use replace_all to rename variables/strings throughout the file

Important about line numbers:
- Read tool shows: "  123\t    def function():"
- The line number prefix is: "  123\t" (spaces + number + tab)
- The actual file content is: "    def function():" (everything after the tab)
- NEVER include the line number prefix in old_string or new_string

Examples:
- Replace a function: old_string="def old():\n    pass", new_string="def new():\n    return 42"
- Rename variable: old_string="old_name", new_string="new_name", replace_all=true"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to modify",
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact text to replace (must match exactly including whitespace)",
                },
                "new_string": {
                    "type": "string",
                    "description": "The text to replace it with (must be different from old_string)",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences (default: false)",
                    "default": False,
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute file edit.

        Args:
            params: Edit parameters
            context: Tool execution context

        Returns:
            Dictionary containing edit results
        """
        file_path = params.get("file_path")
        old_string = params.get("old_string")
        new_string = params.get("new_string")
        replace_all = params.get("replace_all", False)

        if not file_path:
            return {
                "success": False,
                "error": "file_path parameter is required",
            }

        if old_string is None:
            return {
                "success": False,
                "error": "old_string parameter is required",
            }

        if new_string is None:
            return {
                "success": False,
                "error": "new_string parameter is required",
            }

        if old_string == new_string:
            return {
                "success": False,
                "error": "old_string and new_string must be different",
            }

        # Convert to absolute path
        if not os.path.isabs(file_path):
            file_path = os.path.join(self._default_directory, file_path)

        try:
            # Check if file exists
            if not os.path.isfile(file_path):
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                }

            # Read current content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if old_string exists in file
            if old_string not in content:
                return {
                    "success": False,
                    "error": f"String not found in file. Make sure to read the file first and use exact string including whitespace.",
                }

            # Check if old_string is unique (if not replacing all)
            if not replace_all:
                occurrences = content.count(old_string)
                if occurrences > 1:
                    return {
                        "success": False,
                        "error": f"String appears {occurrences} times in file. Use replace_all=true to replace all occurrences, or provide a larger unique string.",
                    }

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacement_count = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacement_count = 1

            # Write new content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            # Generate diff summary
            old_lines = content.count("\n") + 1
            new_lines = new_content.count("\n") + 1
            lines_changed = abs(new_lines - old_lines)

            return {
                "success": True,
                "file": file_path,
                "replacements": replacement_count,
                "old_lines": old_lines,
                "new_lines": new_lines,
                "lines_changed": lines_changed,
                "message": f"Successfully replaced {replacement_count} occurrence(s) in {file_path}",
            }

        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied: {file_path}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Edit failed: {str(e)}",
            }
