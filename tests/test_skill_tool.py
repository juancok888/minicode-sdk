"""Tests for SkillTool."""

import os
import tempfile
from pathlib import Path

import pytest

from minicode.session.message import ToolContext
from minicode.skills.loader import SkillLoader
from minicode.tools.builtin.skill import SkillTool


@pytest.fixture
def temp_skill_dir():
    """Create a temporary skill directory with test skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        skills_dir.mkdir()

        # Create skill 1: pdf
        pdf_dir = skills_dir / "pdf"
        pdf_dir.mkdir()
        (pdf_dir / "SKILL.md").write_text(
            """---
name: pdf
description: Extract and analyze PDF files
---

This skill helps you extract text and analyze PDF documents.

## Usage
1. Use pdf extraction library
2. Parse content
3. Return structured data
"""
        )

        # Create skill 2: xlsx
        xlsx_dir = skills_dir / "xlsx"
        xlsx_dir.mkdir()
        (xlsx_dir / "SKILL.md").write_text(
            """---
name: xlsx
description: Process Excel spreadsheets
---

This skill helps you process and analyze Excel files.

## Features
- Read multiple sheets
- Parse formulas
- Export to CSV
"""
        )

        # Create skill 3: invalid (missing description)
        invalid_dir = skills_dir / "invalid"
        invalid_dir.mkdir()
        (invalid_dir / "SKILL.md").write_text(
            """---
name: invalid
---

This skill is invalid due to missing description.
"""
        )

        yield skills_dir


@pytest.fixture
def skill_loader(temp_skill_dir):
    """Create a SkillLoader with temp directory."""
    return SkillLoader(skill_dirs=[str(temp_skill_dir)])


@pytest.fixture
def skill_tool(skill_loader):
    """Create a SkillTool instance."""
    return SkillTool(skill_loader=skill_loader)


class TestSkillToolBasics:
    """Test basic SkillTool functionality."""

    def test_tool_name(self, skill_tool):
        """Test tool name is 'skill'."""
        assert skill_tool.name == "skill"

    def test_description_no_skills(self):
        """Test description when no skills are available."""
        empty_loader = SkillLoader(skill_dirs=["/nonexistent/path"])
        tool = SkillTool(skill_loader=empty_loader)
        description = tool.description

        assert "Execute a skill within the main conversation" in description
        assert "<skills_instructions>" in description
        assert "<available_skills>" in description
        assert "</available_skills>" in description
        # Should be empty
        assert "<skill>" not in description

    def test_description_with_skills(self, skill_tool):
        """Test description includes available skills."""
        description = skill_tool.description

        assert "Execute a skill within the main conversation" in description
        assert "<available_skills>" in description
        assert "<skill>" in description
        assert "<name>pdf</name>" in description
        assert "<description>Extract and analyze PDF files</description>" in description
        assert "<name>xlsx</name>" in description
        assert "<description>Process Excel spreadsheets</description>" in description

    def test_parameters_schema(self, skill_tool):
        """Test parameters schema."""
        schema = skill_tool.parameters_schema

        assert schema["type"] == "object"
        assert "skill" in schema["properties"]
        assert schema["properties"]["skill"]["type"] == "string"
        assert "skill" in schema["required"]
        assert schema["additionalProperties"] is False


class TestSkillExecution:
    """Test skill execution."""

    @pytest.mark.asyncio
    async def test_execute_valid_skill(self, skill_tool):
        """Test executing a valid skill."""
        context = ToolContext(agent_name="test_agent")
        result = await skill_tool.execute({"skill": "pdf"}, context)

        assert result["success"] is True
        assert "## Skill: pdf" in result["data"]
        assert "**Base directory**:" in result["data"]
        assert "This skill helps you extract text and analyze PDF documents." in result["data"]
        assert "## Usage" in result["data"]
        assert result["skill_name"] == "pdf"
        assert "skill_dir" in result

    @pytest.mark.asyncio
    async def test_execute_another_skill(self, skill_tool):
        """Test executing another skill."""
        context = ToolContext(agent_name="test_agent")
        result = await skill_tool.execute({"skill": "xlsx"}, context)

        assert result["success"] is True
        assert "## Skill: xlsx" in result["data"]
        assert "This skill helps you process and analyze Excel files." in result["data"]
        assert "## Features" in result["data"]
        assert "- Read multiple sheets" in result["data"]
        assert result["skill_name"] == "xlsx"

    @pytest.mark.asyncio
    async def test_execute_nonexistent_skill(self, skill_tool):
        """Test executing a non-existent skill raises error."""
        context = ToolContext(agent_name="test_agent")

        with pytest.raises(ValueError) as exc_info:
            await skill_tool.execute({"skill": "nonexistent"}, context)

        assert 'Skill "nonexistent" not found' in str(exc_info.value)
        assert "Available skills:" in str(exc_info.value)
        assert "pdf" in str(exc_info.value)
        assert "xlsx" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_no_skills_available(self):
        """Test executing when no skills are available."""
        empty_loader = SkillLoader(skill_dirs=["/nonexistent/path"])
        tool = SkillTool(skill_loader=empty_loader)
        context = ToolContext(agent_name="test_agent")

        with pytest.raises(ValueError) as exc_info:
            await tool.execute({"skill": "anything"}, context)

        assert 'Skill "anything" not found' in str(exc_info.value)
        assert "Available skills: none" in str(exc_info.value)


class TestSkillLoading:
    """Test skill loading behavior."""

    def test_skills_loaded_lazily(self, skill_tool):
        """Test skills are loaded lazily."""
        # Before accessing description or executing, skills should not be loaded
        assert skill_tool._skills_loaded is False

        # Accessing description triggers loading
        _ = skill_tool.description
        assert skill_tool._skills_loaded is True
        assert len(skill_tool._skills) == 2  # pdf and xlsx (invalid is skipped)

    def test_skills_only_valid_ones_loaded(self, skill_tool):
        """Test only valid skills are loaded."""
        _ = skill_tool.description  # Trigger loading

        skill_names = [s.name for s in skill_tool._skills]
        assert "pdf" in skill_names
        assert "xlsx" in skill_names
        assert "invalid" not in skill_names  # Missing description


class TestSkillToolIntegration:
    """Test SkillTool integration with SkillLoader."""

    def test_default_skill_loader(self):
        """Test SkillTool creates default SkillLoader if none provided."""
        tool = SkillTool()
        assert tool._skill_loader is not None
        assert isinstance(tool._skill_loader, SkillLoader)

    def test_custom_skill_loader(self, skill_loader):
        """Test SkillTool uses custom SkillLoader."""
        tool = SkillTool(skill_loader=skill_loader)
        assert tool._skill_loader is skill_loader

    @pytest.mark.asyncio
    async def test_skill_content_preserved(self, skill_tool):
        """Test skill content is returned as-is without modification."""
        context = ToolContext(agent_name="test_agent")
        result = await skill_tool.execute({"skill": "pdf"}, context)

        # Check that the markdown content is preserved
        data = result["data"]
        assert "This skill helps you extract text and analyze PDF documents." in data
        assert "## Usage" in data
        assert "1. Use pdf extraction library" in data
        assert "2. Parse content" in data
        assert "3. Return structured data" in data


class TestEdgeCases:
    """Test edge cases."""

    def test_multiple_skill_tools_independent(self, temp_skill_dir):
        """Test multiple SkillTool instances are independent."""
        loader1 = SkillLoader(skill_dirs=[str(temp_skill_dir)])
        loader2 = SkillLoader(skill_dirs=[str(temp_skill_dir)])

        tool1 = SkillTool(skill_loader=loader1)
        tool2 = SkillTool(skill_loader=loader2)

        # Trigger loading on tool1
        _ = tool1.description
        assert tool1._skills_loaded is True
        assert tool2._skills_loaded is False  # tool2 not affected

    @pytest.mark.asyncio
    async def test_skill_with_special_characters(self, temp_skill_dir):
        """Test skill with special characters in content."""
        # Create a skill with special markdown characters
        special_dir = temp_skill_dir / "special"
        special_dir.mkdir()
        (special_dir / "SKILL.md").write_text(
            """---
name: special
description: Skill with special characters
---

This skill has special characters: **bold**, *italic*, `code`, and [links](http://example.com).

Also has:
- Lists
- And more

> Blockquotes too
"""
        )

        loader = SkillLoader(skill_dirs=[str(temp_skill_dir)])
        tool = SkillTool(skill_loader=loader)
        context = ToolContext(agent_name="test_agent")

        result = await tool.execute({"skill": "special"}, context)

        assert result["success"] is True
        assert "**bold**" in result["data"]
        assert "*italic*" in result["data"]
        assert "`code`" in result["data"]
        assert "[links](http://example.com)" in result["data"]
        assert "> Blockquotes too" in result["data"]

    def test_description_caching(self, skill_tool):
        """Test that description doesn't reload skills multiple times."""
        # First call loads skills
        desc1 = skill_tool.description
        assert skill_tool._skills_loaded is True
        skills_count1 = len(skill_tool._skills)

        # Second call uses cached skills
        desc2 = skill_tool.description
        skills_count2 = len(skill_tool._skills)

        assert desc1 == desc2
        assert skills_count1 == skills_count2
        assert skills_count1 == 2  # pdf and xlsx
