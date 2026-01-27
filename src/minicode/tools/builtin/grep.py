"""Grep search tool for minicode SDK with ripgrep and Python fallback."""

import asyncio
import fnmatch
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import regex

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool


# File type to extension mapping (common types)
FILE_TYPE_EXTENSIONS = {
    "py": ["*.py", "*.pyi"],
    "js": ["*.js", "*.jsx"],
    "ts": ["*.ts", "*.tsx"],
    "go": ["*.go"],
    "rust": ["*.rs"],
    "java": ["*.java"],
    "cpp": ["*.cpp", "*.cc", "*.cxx", "*.hpp", "*.h"],
    "c": ["*.c", "*.h"],
    "html": ["*.html", "*.htm"],
    "css": ["*.css", "*.scss", "*.sass"],
    "md": ["*.md", "*.markdown"],
    "json": ["*.json"],
    "yaml": ["*.yaml", "*.yml"],
    "xml": ["*.xml"],
    "sh": ["*.sh", "*.bash"],
}


class GrepTool(BaseTool):
    """Powerful search tool with ripgrep and Python fallback.

    Supports full regex syntax and multiple output modes.
    Uses ripgrep if available, falls back to Python regex implementation.
    """

    def __init__(self, default_directory: Optional[str] = None):
        """Initialize Grep tool.

        Args:
            default_directory: Default directory to search in.
                             If None, uses current working directory.
        """
        self._default_directory = default_directory or str(Path.cwd())
        self._rg_path = shutil.which("rg")
        self._use_ripgrep = self._rg_path is not None

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "grep"

    @property
    def description(self) -> str:
        """Get the tool description."""
        backend = "ripgrep" if self._use_ripgrep else "Python regex"
        return f"""Powerful search tool for searching code (using {backend}).

Supports:
- Full regex syntax (e.g., "log.*Error", "function\\s+\\w+")
- File filtering by glob patterns or file types
- Multiple output modes: content (with context), files only, or counts
- Case-insensitive search
- Multiline matching

Usage notes:
- ALWAYS use Grep for search tasks, not bash grep/rg commands
- Output is limited to 100 matches by default
- Line numbers are included in content mode
- Files are sorted by modification time (newest first)

Examples:
- Search for "TODO" in Python files: pattern="TODO", type="py"
- Search for function definitions: pattern="def\\s+\\w+"
- Case-insensitive search: pattern="error", case_insensitive=true"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for in file contents",
                },
                "path": {
                    "type": "string",
                    "description": "The directory to search in. Defaults to current working directory.",
                },
                "glob": {
                    "type": "string",
                    "description": "File pattern to filter (e.g., '*.js', '*.{ts,tsx}')",
                },
                "type": {
                    "type": "string",
                    "description": "File type to search (js, py, rust, go, java, etc.)",
                },
                "case_insensitive": {
                    "type": "boolean",
                    "description": "Perform case-insensitive search",
                    "default": False,
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["content", "files", "count"],
                    "description": "Output mode: content (show matches), files (paths only), count (match counts)",
                    "default": "content",
                },
                "context_lines": {
                    "type": "integer",
                    "description": "Number of context lines to show before and after matches (content mode only)",
                    "default": 0,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of matches to return",
                    "default": 100,
                },
            },
            "required": ["pattern"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute grep search.

        Args:
            params: Search parameters
            context: Tool execution context

        Returns:
            Dictionary containing search results
        """
        pattern = params.get("pattern")
        if not pattern:
            return {
                "success": False,
                "error": "pattern parameter is required",
            }

        search_path = params.get("path", self._default_directory)
        glob_pattern = params.get("glob")
        file_type = params.get("type")
        case_insensitive = params.get("case_insensitive", False)
        output_mode = params.get("output_mode", "content")
        context_lines = params.get("context_lines", 0)
        limit = params.get("limit", 100)

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

            # Use ripgrep if available, otherwise fallback to Python
            if self._use_ripgrep:
                result = await self._search_with_ripgrep(
                    pattern=pattern,
                    search_path=search_path,
                    glob_pattern=glob_pattern,
                    file_type=file_type,
                    case_insensitive=case_insensitive,
                    output_mode=output_mode,
                    context_lines=context_lines,
                    limit=limit,
                )
            else:
                result = await self._search_with_python(
                    pattern=pattern,
                    search_path=search_path,
                    glob_pattern=glob_pattern,
                    file_type=file_type,
                    case_insensitive=case_insensitive,
                    output_mode=output_mode,
                    limit=limit,
                )

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Grep search failed: {str(e)}",
            }

    async def _search_with_ripgrep(
        self,
        pattern: str,
        search_path: str,
        glob_pattern: Optional[str],
        file_type: Optional[str],
        case_insensitive: bool,
        output_mode: str,
        context_lines: int,
        limit: int,
    ) -> Dict[str, Any]:
        """Search using ripgrep."""
        cmd = [
            self._rg_path,
            "--no-heading",
            "--line-number",
            "--hidden",
            "--follow",
        ]

        if case_insensitive:
            cmd.append("--ignore-case")

        if output_mode == "files":
            cmd.append("--files-with-matches")
        elif output_mode == "count":
            cmd.append("--count")

        if context_lines > 0 and output_mode == "content":
            cmd.extend(["--context", str(context_lines)])

        if glob_pattern:
            cmd.extend(["--glob", glob_pattern])

        if file_type:
            cmd.extend(["--type", file_type])

        cmd.extend([pattern, search_path])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 1:
            return {
                "success": True,
                "matches": [],
                "count": 0,
                "message": "No matches found",
                "backend": "ripgrep",
            }

        if process.returncode not in (0, 1):
            error_msg = stderr.decode("utf-8", errors="replace")
            return {
                "success": False,
                "error": f"Ripgrep failed: {error_msg}",
            }

        output_text = stdout.decode("utf-8", errors="replace")
        matches = self._parse_ripgrep_output(output_text, output_mode, limit)

        return {
            "success": True,
            "matches": matches,
            "count": len(matches),
            "truncated": len(matches) >= limit,
            "pattern": pattern,
            "backend": "ripgrep",
        }

    async def _search_with_python(
        self,
        pattern: str,
        search_path: str,
        glob_pattern: Optional[str],
        file_type: Optional[str],
        case_insensitive: bool,
        output_mode: str,
        limit: int,
    ) -> Dict[str, Any]:
        """Search using Python regex (fallback)."""
        # Compile regex pattern
        flags = regex.IGNORECASE if case_insensitive else 0
        try:
            compiled_pattern = regex.compile(pattern, flags)
        except regex.error as e:
            return {
                "success": False,
                "error": f"Invalid regex pattern: {str(e)}",
            }

        # Determine file patterns
        patterns = []
        if glob_pattern:
            patterns.append(glob_pattern)
        if file_type and file_type in FILE_TYPE_EXTENSIONS:
            patterns.extend(FILE_TYPE_EXTENSIONS[file_type])
        if not patterns:
            patterns = ["*"]

        # Search files
        matches: List[Tuple[str, int, str, float]] = []
        search_dir = Path(search_path)

        for file_path in search_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # Check if file matches pattern
            if not any(fnmatch.fnmatch(file_path.name, pat) for pat in patterns):
                continue

            try:
                # Skip binary files
                with open(file_path, "rb") as f:
                    chunk = f.read(1024)
                    if b"\x00" in chunk:
                        continue

                # Search in file
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if compiled_pattern.search(line):
                            mtime = file_path.stat().st_mtime
                            content = line.rstrip("\n\r")
                            if len(content) > 500:
                                content = content[:500] + "..."
                            matches.append((str(file_path), line_num, content, mtime))

                            if len(matches) >= limit:
                                break

                if len(matches) >= limit:
                    break

            except (OSError, PermissionError, UnicodeDecodeError):
                continue

        # Sort by modification time (newest first)
        matches.sort(key=lambda x: x[3], reverse=True)

        # Format results based on output mode
        if output_mode == "files":
            seen_files = set()
            result_matches = []
            for file_path, _, _, _ in matches:
                if file_path not in seen_files:
                    seen_files.add(file_path)
                    result_matches.append({"file": file_path})
        elif output_mode == "count":
            file_counts: Dict[str, int] = {}
            for file_path, _, _, _ in matches:
                file_counts[file_path] = file_counts.get(file_path, 0) + 1
            result_matches = [
                {"file": file_path, "count": count}
                for file_path, count in file_counts.items()
            ]
        else:  # content mode
            result_matches = [
                {
                    "file": file_path,
                    "line": line_num,
                    "content": content,
                }
                for file_path, line_num, content, _ in matches[:limit]
            ]

        return {
            "success": True,
            "matches": result_matches,
            "count": len(result_matches),
            "truncated": len(matches) >= limit,
            "pattern": pattern,
            "backend": "python-regex",
        }

    def _parse_ripgrep_output(
        self,
        output: str,
        mode: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Parse ripgrep output into structured matches."""
        if not output.strip():
            return []

        lines = output.strip().split("\n")
        matches: List[Dict[str, Any]] = []

        if mode == "files":
            for line in lines[:limit]:
                if line:
                    matches.append({"file": line.strip()})

        elif mode == "count":
            for line in lines[:limit]:
                if ":" in line:
                    file_path, count_str = line.rsplit(":", 1)
                    try:
                        count = int(count_str)
                        matches.append({"file": file_path, "count": count})
                    except ValueError:
                        continue

        else:  # content mode
            for line in lines[:limit]:
                if not line:
                    continue

                parts = line.split(":", 2)
                if len(parts) >= 3:
                    file_path = parts[0]
                    try:
                        line_num = int(parts[1])
                        content = parts[2] if len(parts) > 2 else ""

                        if len(content) > 500:
                            content = content[:500] + "..."

                        matches.append({
                            "file": file_path,
                            "line": line_num,
                            "content": content,
                        })
                    except ValueError:
                        continue

        return matches
