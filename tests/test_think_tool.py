"""Tests for ThinkTool and ThinkManager."""

import pytest

from minicode.session.message import ToolContext
from minicode.tools.builtin.think import ThinkTool, ThinkManager


@pytest.fixture
def think_tool():
    """Create a ThinkTool instance."""
    return ThinkTool()


@pytest.fixture
def context():
    """Create a ToolContext instance."""
    return ToolContext(agent_name="test_agent")


class TestThinkToolBasics:
    """Test basic ThinkTool functionality."""

    def test_tool_name(self, think_tool):
        """Test tool name is 'think'."""
        assert think_tool.name == "think"

    def test_description(self, think_tool):
        """Test tool has description."""
        description = think_tool.description
        assert "Record your thinking and reasoning process" in description
        assert "analysis" in description
        assert "planning" in description
        assert "reflection" in description
        assert "reasoning" in description
        assert "observation" in description

    def test_parameters_schema(self, think_tool):
        """Test parameters schema."""
        schema = think_tool.parameters_schema

        assert schema["type"] == "object"
        assert "type" in schema["properties"]
        assert "content" in schema["properties"]
        assert "title" in schema["properties"]
        assert "tags" in schema["properties"]

        # Check enum for type
        assert schema["properties"]["type"]["enum"] == [
            "analysis",
            "planning",
            "reflection",
            "reasoning",
            "observation",
        ]

        # Check required fields
        assert set(schema["required"]) == {"type", "content"}


class TestThinkExecution:
    """Test think execution."""

    @pytest.mark.asyncio
    async def test_execute_analysis(self, think_tool, context):
        """Test executing analysis thinking."""
        result = await think_tool.execute(
            {
                "type": "analysis",
                "content": "The code has three components: loading, processing, visualization.",
            },
            context,
        )

        assert result["success"] is True
        assert "think_id" in result
        assert len(result["think_id"]) == 8  # UUID first 8 chars
        assert "Thinking recorded" in result["message"]
        assert "🔍" in result["output"]  # Analysis emoji
        assert "ANALYSIS" in result["output"]
        assert "The code has three components" in result["output"]

    @pytest.mark.asyncio
    async def test_execute_planning(self, think_tool, context):
        """Test executing planning thinking."""
        result = await think_tool.execute(
            {
                "type": "planning",
                "content": "Step 1: Update schema\nStep 2: Modify API\nStep 3: Update frontend",
                "title": "Feature Implementation Plan",
            },
            context,
        )

        assert result["success"] is True
        assert "📋" in result["output"]  # Planning emoji
        assert "PLANNING" in result["output"]
        assert "Feature Implementation Plan" in result["output"]
        assert "Step 1: Update schema" in result["output"]

    @pytest.mark.asyncio
    async def test_execute_reflection(self, think_tool, context):
        """Test executing reflection thinking."""
        result = await think_tool.execute(
            {
                "type": "reflection",
                "content": "My previous approach failed because I didn't verify the data.",
                "tags": ["debugging", "lesson-learned"],
            },
            context,
        )

        assert result["success"] is True
        assert "💭" in result["output"]  # Reflection emoji
        assert "REFLECTION" in result["output"]
        assert "previous approach failed" in result["output"]
        assert "debugging" in result["output"]
        assert "lesson-learned" in result["output"]

    @pytest.mark.asyncio
    async def test_execute_reasoning(self, think_tool, context):
        """Test executing reasoning thinking."""
        result = await think_tool.execute(
            {"type": "reasoning", "content": "If A > B and B > C, then A > C."},
            context,
        )

        assert result["success"] is True
        assert "🧠" in result["output"]  # Reasoning emoji
        assert "REASONING" in result["output"]

    @pytest.mark.asyncio
    async def test_execute_observation(self, think_tool, context):
        """Test executing observation thinking."""
        result = await think_tool.execute(
            {"type": "observation", "content": "The function is called 100 times per second."},
            context,
        )

        assert result["success"] is True
        assert "👁️" in result["output"]  # Observation emoji
        assert "OBSERVATION" in result["output"]

    @pytest.mark.asyncio
    async def test_execute_empty_content_error(self, think_tool, context):
        """Test that empty content raises error."""
        with pytest.raises(ValueError) as exc_info:
            await think_tool.execute({"type": "analysis", "content": ""}, context)

        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_whitespace_content_error(self, think_tool, context):
        """Test that whitespace-only content raises error."""
        with pytest.raises(ValueError) as exc_info:
            await think_tool.execute({"type": "analysis", "content": "   \n\t  "}, context)

        assert "cannot be empty" in str(exc_info.value)


class TestThinkStorage:
    """Test think record storage."""

    @pytest.mark.asyncio
    async def test_thinks_stored_in_context(self, think_tool, context):
        """Test think records are stored in context metadata."""
        await think_tool.execute(
            {"type": "analysis", "content": "First thought"}, context
        )

        assert "think_records" in context.metadata
        assert len(context.metadata["think_records"]) == 1
        assert context.metadata["think_records"][0]["content"] == "First thought"

    @pytest.mark.asyncio
    async def test_multiple_thinks_stored(self, think_tool, context):
        """Test multiple think records are accumulated."""
        await think_tool.execute({"type": "analysis", "content": "Thought 1"}, context)
        await think_tool.execute({"type": "planning", "content": "Thought 2"}, context)
        await think_tool.execute(
            {"type": "reflection", "content": "Thought 3"}, context
        )

        assert len(context.metadata["think_records"]) == 3
        assert context.metadata["think_records"][0]["type"] == "analysis"
        assert context.metadata["think_records"][1]["type"] == "planning"
        assert context.metadata["think_records"][2]["type"] == "reflection"

    @pytest.mark.asyncio
    async def test_think_record_structure(self, think_tool, context):
        """Test think record has correct structure."""
        result = await think_tool.execute(
            {
                "type": "analysis",
                "content": "Test content",
                "title": "Test title",
                "tags": ["tag1", "tag2"],
            },
            context,
        )

        think_id = result["think_id"]
        record = context.metadata["think_records"][0]

        assert record["id"] == think_id
        assert record["type"] == "analysis"
        assert record["content"] == "Test content"
        assert record["title"] == "Test title"
        assert record["tags"] == ["tag1", "tag2"]
        assert record["agent_name"] == "test_agent"
        assert "timestamp" in record


class TestThinkManager:
    """Test ThinkManager functionality."""

    @pytest.mark.asyncio
    async def test_get_all_thinks_empty(self, context):
        """Test getting all thinks when none exist."""
        thinks = ThinkManager.get_all_thinks(context)
        assert thinks == []

    @pytest.mark.asyncio
    async def test_get_all_thinks(self, think_tool, context):
        """Test getting all think records."""
        await think_tool.execute({"type": "analysis", "content": "Thought 1"}, context)
        await think_tool.execute({"type": "planning", "content": "Thought 2"}, context)

        thinks = ThinkManager.get_all_thinks(context)
        assert len(thinks) == 2

    @pytest.mark.asyncio
    async def test_get_thinks_by_type(self, think_tool, context):
        """Test filtering thinks by type."""
        await think_tool.execute({"type": "analysis", "content": "Analysis 1"}, context)
        await think_tool.execute({"type": "planning", "content": "Plan 1"}, context)
        await think_tool.execute({"type": "analysis", "content": "Analysis 2"}, context)

        analysis_thinks = ThinkManager.get_thinks_by_type(context, "analysis")
        planning_thinks = ThinkManager.get_thinks_by_type(context, "planning")

        assert len(analysis_thinks) == 2
        assert len(planning_thinks) == 1
        assert all(t["type"] == "analysis" for t in analysis_thinks)
        assert all(t["type"] == "planning" for t in planning_thinks)

    @pytest.mark.asyncio
    async def test_get_thinks_by_tags(self, think_tool, context):
        """Test filtering thinks by tags."""
        await think_tool.execute(
            {"type": "analysis", "content": "T1", "tags": ["bug", "frontend"]}, context
        )
        await think_tool.execute(
            {"type": "planning", "content": "T2", "tags": ["feature"]}, context
        )
        await think_tool.execute(
            {"type": "reflection", "content": "T3", "tags": ["bug", "backend"]}, context
        )

        bug_thinks = ThinkManager.get_thinks_by_tags(context, ["bug"])
        feature_thinks = ThinkManager.get_thinks_by_tags(context, ["feature"])
        backend_thinks = ThinkManager.get_thinks_by_tags(context, ["backend"])

        assert len(bug_thinks) == 2  # T1 and T3
        assert len(feature_thinks) == 1  # T2
        assert len(backend_thinks) == 1  # T3

    @pytest.mark.asyncio
    async def test_get_think_by_id(self, think_tool, context):
        """Test getting specific think by ID."""
        result1 = await think_tool.execute(
            {"type": "analysis", "content": "First"}, context
        )
        result2 = await think_tool.execute(
            {"type": "planning", "content": "Second"}, context
        )

        think1 = ThinkManager.get_think_by_id(context, result1["think_id"])
        think2 = ThinkManager.get_think_by_id(context, result2["think_id"])

        assert think1["content"] == "First"
        assert think2["content"] == "Second"

    @pytest.mark.asyncio
    async def test_get_think_by_id_not_found(self, context):
        """Test getting think by non-existent ID."""
        think = ThinkManager.get_think_by_id(context, "nonexistent")
        assert think is None

    @pytest.mark.asyncio
    async def test_clear_thinks(self, think_tool, context):
        """Test clearing all think records."""
        await think_tool.execute({"type": "analysis", "content": "T1"}, context)
        await think_tool.execute({"type": "planning", "content": "T2"}, context)

        assert len(ThinkManager.get_all_thinks(context)) == 2

        count = ThinkManager.clear_thinks(context)
        assert count == 2
        assert len(ThinkManager.get_all_thinks(context)) == 0

    @pytest.mark.asyncio
    async def test_clear_thinks_empty(self, context):
        """Test clearing when no thinks exist."""
        count = ThinkManager.clear_thinks(context)
        assert count == 0

    @pytest.mark.asyncio
    async def test_format_think_summary_empty(self, context):
        """Test formatting summary when no thinks exist."""
        summary = ThinkManager.format_think_summary(context)
        assert "No thinking records found" in summary

    @pytest.mark.asyncio
    async def test_format_think_summary(self, think_tool, context):
        """Test formatting summary of think records."""
        await think_tool.execute(
            {"type": "analysis", "content": "A" * 150, "title": "Long analysis"}, context
        )
        await think_tool.execute(
            {"type": "planning", "content": "Short plan", "title": "Quick plan"}, context
        )
        await think_tool.execute(
            {
                "type": "analysis",
                "content": "Another analysis",
                "title": "Second analysis",
            },
            context,
        )

        summary = ThinkManager.format_think_summary(context)

        assert "Thinking Summary (3 records)" in summary
        assert "ANALYSIS (2)" in summary
        assert "PLANNING (1)" in summary
        assert "Long analysis" in summary
        assert "Quick plan" in summary
        assert "Second analysis" in summary
        # Check that long content is truncated
        assert "..." in summary  # Long analysis should be truncated


class TestEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_content_with_special_characters(self, think_tool, context):
        """Test content with special markdown characters."""
        content = "**Bold**, *italic*, `code`, [link](url), # heading"
        result = await think_tool.execute(
            {"type": "analysis", "content": content}, context
        )

        assert result["success"] is True
        assert content in result["output"]

    @pytest.mark.asyncio
    async def test_very_long_content(self, think_tool, context):
        """Test very long content."""
        content = "A" * 10000
        result = await think_tool.execute(
            {"type": "analysis", "content": content}, context
        )

        assert result["success"] is True
        record = context.metadata["think_records"][0]
        assert len(record["content"]) == 10000

    @pytest.mark.asyncio
    async def test_empty_tags_array(self, think_tool, context):
        """Test with empty tags array."""
        result = await think_tool.execute(
            {"type": "analysis", "content": "Test", "tags": []}, context
        )

        assert result["success"] is True
        record = context.metadata["think_records"][0]
        assert record["tags"] == []

    @pytest.mark.asyncio
    async def test_no_optional_fields(self, think_tool, context):
        """Test with only required fields."""
        result = await think_tool.execute(
            {"type": "analysis", "content": "Test"}, context
        )

        assert result["success"] is True
        record = context.metadata["think_records"][0]
        assert record["title"] is None
        assert record["tags"] == []

    @pytest.mark.asyncio
    async def test_unicode_content(self, think_tool, context):
        """Test with unicode content."""
        content = "中文思考 🤔 émoji"
        result = await think_tool.execute(
            {"type": "analysis", "content": content}, context
        )

        assert result["success"] is True
        assert content in result["output"]

    @pytest.mark.asyncio
    async def test_multiline_content(self, think_tool, context):
        """Test with multiline content."""
        content = """Line 1
Line 2
Line 3"""
        result = await think_tool.execute(
            {"type": "analysis", "content": content}, context
        )

        assert result["success"] is True
        assert "Line 1" in result["output"]
        assert "Line 2" in result["output"]
        assert "Line 3" in result["output"]
