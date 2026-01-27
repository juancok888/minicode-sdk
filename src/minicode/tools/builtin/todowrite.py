"""TodoWrite tool for managing structured task lists."""

from typing import Any, Dict, List

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool


class TodoWriteTool(BaseTool):
    """Tool for creating and managing structured task lists.

    Helps track progress and organize work during coding sessions.
    """

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "todo_write"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return """Create and manage structured task lists for tracking progress.

Features:
- Track multiple tasks with status (pending/in_progress/completed)
- Each task has content (what to do) and activeForm (current state)
- Provides visibility into agent progress
- Helps organize complex multi-step tasks

Task States:
- pending: Task not yet started
- in_progress: Currently working on (should be exactly ONE task)
- completed: Task finished successfully

Usage notes:
- Use this tool proactively for non-trivial tasks (3+ steps)
- Mark tasks complete IMMEDIATELY after finishing
- Exactly ONE task should be in_progress at any time
- Update status in real-time as you work

When to use:
- Complex multi-step tasks
- User provides multiple tasks
- Non-trivial implementations
- After receiving new instructions

When NOT to use:
- Single straightforward tasks
- Trivial operations (< 3 steps)
- Purely conversational requests

Examples:
- Complex feature: Create todos for design, implementation, testing, documentation
- Bug fix: Create todos for reproduction, fix, testing, verification
- Multiple tasks: User lists several things to do"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "Updated todo list",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Task description in imperative form (e.g., 'Run tests')",
                                "minLength": 1,
                            },
                            "activeForm": {
                                "type": "string",
                                "description": "Present continuous form shown during execution (e.g., 'Running tests')",
                                "minLength": 1,
                            },
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                                "description": "Task status",
                            },
                        },
                        "required": ["content", "status", "activeForm"],
                    },
                },
            },
            "required": ["todos"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute todo list update.

        Args:
            params: Todo list parameters
            context: Tool execution context

        Returns:
            Dictionary containing update result
        """
        todos = params.get("todos")
        if todos is None:
            return {
                "success": False,
                "error": "todos parameter is required",
            }

        # Validate todos is a list
        if not isinstance(todos, list):
            return {
                "success": False,
                "error": "todos must be a list",
            }

        # Validate each todo
        for i, todo in enumerate(todos):
            if not isinstance(todo, dict):
                return {
                    "success": False,
                    "error": f"Todo {i} must be a dictionary",
                }

            # Check required fields
            for field in ["content", "status", "activeForm"]:
                if field not in todo:
                    return {
                        "success": False,
                        "error": f"Todo {i} missing required field: {field}",
                    }

            # Validate status
            status = todo["status"]
            if status not in ["pending", "in_progress", "completed"]:
                return {
                    "success": False,
                    "error": f"Todo {i} has invalid status: {status}",
                }

            # Validate non-empty strings
            if not todo["content"].strip():
                return {
                    "success": False,
                    "error": f"Todo {i} has empty content",
                }

            if not todo["activeForm"].strip():
                return {
                    "success": False,
                    "error": f"Todo {i} has empty activeForm",
                }

        # Count in-progress tasks
        in_progress_count = sum(1 for todo in todos if todo["status"] == "in_progress")

        # Warn if more than one in_progress (but don't fail)
        warning = None
        if in_progress_count > 1:
            warning = f"Warning: {in_progress_count} tasks are in_progress. Best practice is to have exactly 1."
        elif in_progress_count == 0 and any(todo["status"] == "pending" for todo in todos):
            warning = "Warning: No task is in_progress. Consider marking the current task as in_progress."

        # Count by status
        status_counts = {
            "pending": sum(1 for todo in todos if todo["status"] == "pending"),
            "in_progress": in_progress_count,
            "completed": sum(1 for todo in todos if todo["status"] == "completed"),
        }

        # Store todos in context metadata (optional, for tracking)
        if hasattr(context, "metadata"):
            context.metadata["todos"] = todos

        result = {
            "success": True,
            "message": f"Updated task list: {len(todos)} total tasks",
            "status_counts": status_counts,
            "total_tasks": len(todos),
        }

        if warning:
            result["warning"] = warning

        return result
