"""Think tool for recording agent's reasoning process.

This tool allows agents to explicitly record their thinking steps,
making the reasoning process visible and traceable.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool

ThinkType = Literal["analysis", "planning", "reflection", "reasoning", "observation"]


class ThinkTool(BaseTool):
    """Tool for recording agent's thinking and reasoning process.

    This tool allows agents to explicitly document their thought process,
    making complex reasoning visible and traceable. Think records are stored
    in the session context and can be referenced later.

    Examples:
        Analysis:
            "I notice the code has three major components: data loading,
            processing, and visualization. The bug is likely in the processing
            step because..."

        Planning:
            "To implement this feature, I'll need to: 1) Update the database
            schema, 2) Modify the API endpoints, 3) Update the frontend..."

        Reflection:
            "My previous approach didn't work because I assumed the data was
            sorted. I should verify data properties before processing."
    """

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "think"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return """Record your thinking and reasoning process.

Use this tool to make your reasoning explicit and visible. This helps with:
- Complex problem-solving that requires multiple steps
- Planning before taking action
- Reflecting on previous attempts
- Analyzing code or data before making decisions

Think types:
- analysis: Analyzing a problem, code, or situation
- planning: Planning steps or approach before execution
- reflection: Reflecting on what worked or didn't work
- reasoning: Step-by-step logical reasoning
- observation: Noting important observations or patterns

Your thinking will be recorded and visible to users, helping them understand
your reasoning process."""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["analysis", "planning", "reflection", "reasoning", "observation"],
                    "description": "The type of thinking being recorded",
                },
                "content": {
                    "type": "string",
                    "description": "The thinking content - your reasoning, analysis, or observations",
                },
                "title": {
                    "type": "string",
                    "description": "Optional title or summary of this thinking step",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for categorizing this thought",
                },
            },
            "required": ["type", "content"],
            "additionalProperties": False,
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute the think tool.

        Args:
            params: Parameters containing type, content, and optional title/tags
            context: Tool execution context

        Returns:
            Dict with think record ID and confirmation

        Raises:
            ValueError: If parameters are invalid
        """
        think_type = params["type"]
        content = params["content"]
        title = params.get("title")
        tags = params.get("tags", [])

        # Validate content
        if not content or not content.strip():
            raise ValueError("Think content cannot be empty")

        # Generate unique ID for this think record
        think_id = str(uuid.uuid4())[:8]

        # Create think record
        think_record = {
            "id": think_id,
            "type": think_type,
            "content": content.strip(),
            "title": title,
            "tags": tags,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_name": context.agent_name,
        }

        # Store in context metadata
        if "think_records" not in context.metadata:
            context.metadata["think_records"] = []

        context.metadata["think_records"].append(think_record)

        # Format output for user visibility
        type_emoji = {
            "analysis": "🔍",
            "planning": "📋",
            "reflection": "💭",
            "reasoning": "🧠",
            "observation": "👁️",
        }

        emoji = type_emoji.get(think_type, "💡")
        output_lines = [f"{emoji} **{think_type.upper()}**"]

        if title:
            output_lines.append(f"### {title}")

        output_lines.append("")
        output_lines.append(content.strip())

        if tags:
            output_lines.append("")
            output_lines.append(f"*Tags: {', '.join(tags)}*")

        return {
            "success": True,
            "think_id": think_id,
            "message": f"Thinking recorded (ID: {think_id})",
            "output": "\n".join(output_lines),
        }


class ThinkManager:
    """Manager for querying and analyzing think records.

    This is a utility class (not a tool) for retrieving and analyzing
    think records from a context.
    """

    @staticmethod
    def get_all_thinks(context: ToolContext) -> List[Dict[str, Any]]:
        """Get all think records from context.

        Args:
            context: Tool execution context

        Returns:
            List of think records
        """
        return context.metadata.get("think_records", [])

    @staticmethod
    def get_thinks_by_type(
        context: ToolContext, think_type: ThinkType
    ) -> List[Dict[str, Any]]:
        """Get think records filtered by type.

        Args:
            context: Tool execution context
            think_type: Type of think records to retrieve

        Returns:
            List of think records matching the type
        """
        all_thinks = ThinkManager.get_all_thinks(context)
        return [t for t in all_thinks if t["type"] == think_type]

    @staticmethod
    def get_thinks_by_tags(
        context: ToolContext, tags: List[str]
    ) -> List[Dict[str, Any]]:
        """Get think records filtered by tags.

        Args:
            context: Tool execution context
            tags: Tags to filter by (returns records with ANY of these tags)

        Returns:
            List of think records matching the tags
        """
        all_thinks = ThinkManager.get_all_thinks(context)
        return [t for t in all_thinks if any(tag in t.get("tags", []) for tag in tags)]

    @staticmethod
    def get_think_by_id(
        context: ToolContext, think_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific think record by ID.

        Args:
            context: Tool execution context
            think_id: ID of the think record

        Returns:
            Think record if found, None otherwise
        """
        all_thinks = ThinkManager.get_all_thinks(context)
        for think in all_thinks:
            if think["id"] == think_id:
                return think
        return None

    @staticmethod
    def clear_thinks(context: ToolContext) -> int:
        """Clear all think records from context.

        Args:
            context: Tool execution context

        Returns:
            Number of think records cleared
        """
        count = len(context.metadata.get("think_records", []))
        context.metadata["think_records"] = []
        return count

    @staticmethod
    def format_think_summary(context: ToolContext) -> str:
        """Format a summary of all think records.

        Args:
            context: Tool execution context

        Returns:
            Formatted string summarizing all think records
        """
        all_thinks = ThinkManager.get_all_thinks(context)

        if not all_thinks:
            return "No thinking records found."

        lines = [f"# Thinking Summary ({len(all_thinks)} records)\n"]

        # Group by type
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for think in all_thinks:
            think_type = think["type"]
            if think_type not in by_type:
                by_type[think_type] = []
            by_type[think_type].append(think)

        # Format each type
        for think_type, records in by_type.items():
            lines.append(f"## {think_type.upper()} ({len(records)})")
            for record in records:
                title = record.get("title", "Untitled")
                think_id = record["id"]
                lines.append(f"- [{think_id}] {title}")
                # Show first 100 chars of content
                content_preview = record["content"][:100]
                if len(record["content"]) > 100:
                    content_preview += "..."
                lines.append(f"  {content_preview}")
            lines.append("")

        return "\n".join(lines)
