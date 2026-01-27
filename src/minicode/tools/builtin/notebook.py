"""NotebookEdit tool for editing Jupyter notebook cells."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool


class NotebookEditTool(BaseTool):
    """Tool for editing Jupyter notebook cells.

    Supports replacing, inserting, and deleting cells in .ipynb files.
    """

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "notebook_edit"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return """Edit Jupyter notebook (.ipynb) cells.

Features:
- Replace cell content by cell ID
- Insert new cells at specific positions
- Delete cells by ID
- Support for code and markdown cells
- Preserves notebook metadata and structure

Usage notes:
- Notebook path must be absolute
- Cell IDs are unique identifiers (not indexes)
- Edit modes: replace (default), insert, delete
- Cell types: code, markdown

Examples:
- Replace cell: notebook_path="/path/to.ipynb", cell_id="abc123", new_source="print('hello')"
- Insert cell: notebook_path="/path/to.ipynb", edit_mode="insert", cell_id="abc123", cell_type="code", new_source="x = 1"
- Delete cell: notebook_path="/path/to.ipynb", edit_mode="delete", cell_id="abc123"
"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "notebook_path": {
                    "type": "string",
                    "description": "Absolute path to the Jupyter notebook file",
                },
                "new_source": {
                    "type": "string",
                    "description": "New source code/markdown content for the cell",
                },
                "cell_id": {
                    "type": "string",
                    "description": "ID of the cell to edit (for replace/delete) or insert after (for insert mode)",
                },
                "cell_type": {
                    "type": "string",
                    "enum": ["code", "markdown"],
                    "description": "Type of cell (code or markdown). Required for insert mode.",
                },
                "edit_mode": {
                    "type": "string",
                    "enum": ["replace", "insert", "delete"],
                    "description": "Edit mode: replace (default), insert, or delete",
                    "default": "replace",
                },
            },
            "required": ["notebook_path", "new_source"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute notebook edit.

        Args:
            params: Edit parameters
            context: Tool execution context

        Returns:
            Dictionary containing edit result
        """
        notebook_path = params.get("notebook_path")
        if not notebook_path:
            return {
                "success": False,
                "error": "notebook_path parameter is required",
            }

        # Validate path is absolute
        if not Path(notebook_path).is_absolute():
            return {
                "success": False,
                "error": "notebook_path must be an absolute path",
            }

        # Validate file exists
        nb_path = Path(notebook_path)
        if not nb_path.exists():
            return {
                "success": False,
                "error": f"Notebook file not found: {notebook_path}",
            }

        # Validate file extension
        if nb_path.suffix != ".ipynb":
            return {
                "success": False,
                "error": "File must have .ipynb extension",
            }

        edit_mode = params.get("edit_mode", "replace")
        new_source = params.get("new_source")
        cell_id = params.get("cell_id")
        cell_type = params.get("cell_type")

        try:
            # Load notebook
            with open(nb_path, "r", encoding="utf-8") as f:
                notebook = json.load(f)

            # Validate notebook structure
            if "cells" not in notebook:
                return {
                    "success": False,
                    "error": "Invalid notebook format: missing 'cells' key",
                }

            # Execute edit based on mode
            if edit_mode == "replace":
                result = self._replace_cell(notebook, cell_id, new_source, cell_type)
            elif edit_mode == "insert":
                if not cell_type:
                    return {
                        "success": False,
                        "error": "cell_type is required for insert mode",
                    }
                result = self._insert_cell(notebook, cell_id, new_source, cell_type)
            elif edit_mode == "delete":
                result = self._delete_cell(notebook, cell_id)
            else:
                return {
                    "success": False,
                    "error": f"Invalid edit_mode: {edit_mode}",
                }

            if not result["success"]:
                return result

            # Save notebook
            with open(nb_path, "w", encoding="utf-8") as f:
                json.dump(notebook, f, indent=1, ensure_ascii=False)

            return {
                "success": True,
                "message": result["message"],
                "notebook_path": str(nb_path),
                "cells_count": len(notebook["cells"]),
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON in notebook: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"NotebookEdit failed: {str(e)}",
            }

    def _replace_cell(
        self,
        notebook: Dict[str, Any],
        cell_id: Optional[str],
        new_source: str,
        cell_type: Optional[str],
    ) -> Dict[str, Any]:
        """Replace content of a specific cell.

        Args:
            notebook: Notebook data structure
            cell_id: ID of cell to replace
            new_source: New source content
            cell_type: Optional cell type to change to

        Returns:
            Result dictionary
        """
        if not cell_id:
            return {
                "success": False,
                "error": "cell_id is required for replace mode",
            }

        # Find cell by ID
        cell_index = self._find_cell_by_id(notebook["cells"], cell_id)
        if cell_index is None:
            return {
                "success": False,
                "error": f"Cell with ID '{cell_id}' not found",
            }

        cell = notebook["cells"][cell_index]

        # Update cell type if specified
        if cell_type:
            cell["cell_type"] = cell_type

        # Update source
        # Convert string to list of lines (Jupyter format)
        source_lines = new_source.split("\n")
        # Add newline to all but last line
        cell["source"] = [line + "\n" if i < len(source_lines) - 1 else line
                          for i, line in enumerate(source_lines)]

        # Clear outputs for code cells
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None

        return {
            "success": True,
            "message": f"Replaced cell {cell_id} (type: {cell['cell_type']})",
        }

    def _insert_cell(
        self,
        notebook: Dict[str, Any],
        cell_id: Optional[str],
        new_source: str,
        cell_type: str,
    ) -> Dict[str, Any]:
        """Insert a new cell.

        Args:
            notebook: Notebook data structure
            cell_id: ID of cell to insert after (None = insert at beginning)
            new_source: Source content
            cell_type: Type of new cell

        Returns:
            Result dictionary
        """
        # Determine insert position
        if cell_id:
            cell_index = self._find_cell_by_id(notebook["cells"], cell_id)
            if cell_index is None:
                return {
                    "success": False,
                    "error": f"Cell with ID '{cell_id}' not found",
                }
            insert_pos = cell_index + 1
        else:
            insert_pos = 0

        # Create new cell
        new_cell = self._create_cell(cell_type, new_source)

        # Insert cell
        notebook["cells"].insert(insert_pos, new_cell)

        return {
            "success": True,
            "message": f"Inserted new {cell_type} cell at position {insert_pos}",
        }

    def _delete_cell(
        self,
        notebook: Dict[str, Any],
        cell_id: Optional[str],
    ) -> Dict[str, Any]:
        """Delete a cell.

        Args:
            notebook: Notebook data structure
            cell_id: ID of cell to delete

        Returns:
            Result dictionary
        """
        if not cell_id:
            return {
                "success": False,
                "error": "cell_id is required for delete mode",
            }

        # Find cell by ID
        cell_index = self._find_cell_by_id(notebook["cells"], cell_id)
        if cell_index is None:
            return {
                "success": False,
                "error": f"Cell with ID '{cell_id}' not found",
            }

        # Delete cell
        cell = notebook["cells"].pop(cell_index)

        return {
            "success": True,
            "message": f"Deleted {cell['cell_type']} cell {cell_id}",
        }

    def _find_cell_by_id(
        self,
        cells: List[Dict[str, Any]],
        cell_id: str,
    ) -> Optional[int]:
        """Find cell index by ID.

        Args:
            cells: List of cells
            cell_id: Cell ID to find

        Returns:
            Cell index or None if not found
        """
        for i, cell in enumerate(cells):
            if cell.get("id") == cell_id:
                return i
        return None

    def _create_cell(
        self,
        cell_type: str,
        source: str,
    ) -> Dict[str, Any]:
        """Create a new cell.

        Args:
            cell_type: Type of cell (code/markdown)
            source: Source content

        Returns:
            New cell dictionary
        """
        import uuid

        # Convert source to lines
        source_lines = source.split("\n")
        source_list = [line + "\n" if i < len(source_lines) - 1 else line
                       for i, line in enumerate(source_lines)]

        cell = {
            "id": str(uuid.uuid4()),
            "cell_type": cell_type,
            "metadata": {},
            "source": source_list,
        }

        # Add code-specific fields
        if cell_type == "code":
            cell["execution_count"] = None
            cell["outputs"] = []

        return cell
