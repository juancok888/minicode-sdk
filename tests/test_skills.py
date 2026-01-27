"""Tests for skills system."""

import tempfile
from pathlib import Path

import pytest

from minicode.session.message import ToolContext
from minicode.skills.loader import Skill, SkillLoader


@pytest.fixture
def temp_skills_dir():
    """Create a temporary skills directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_skill_dir(temp_skills_dir):
    """Create a sample skill directory with SKILL.md."""
    skill_dir = temp_skills_dir / "test-skill"
    skill_dir.mkdir()

    skill_content = """---
name: test_skill
description: A test skill for unit testing
---

# Test Skill Content

This is a test skill that processes input.

You can use {input} parameter here.
"""

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(skill_content, encoding="utf-8")

    # Add additional file
    additional_file = skill_dir / "example.py"
    additional_file.write_text("# Example code\nprint('hello')", encoding="utf-8")

    return skill_dir


@pytest.fixture
def skill_with_parameters(temp_skills_dir):
    """Create a skill with parameters schema."""
    skill_dir = temp_skills_dir / "param-skill"
    skill_dir.mkdir()

    skill_content = """---
name: param_skill
description: A skill with parameters
parameters:
  type: object
  properties:
    input:
      type: string
      description: Input text
  required:
    - input
---

# Parameterized Skill

Process: {input}
"""

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(skill_content, encoding="utf-8")

    return skill_dir


@pytest.fixture
def invalid_skill_dir(temp_skills_dir):
    """Create an invalid skill directory (missing required fields)."""
    skill_dir = temp_skills_dir / "invalid-skill"
    skill_dir.mkdir()

    skill_content = """---
name: invalid_skill
---

# Missing description field
"""

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(skill_content, encoding="utf-8")

    return skill_dir


@pytest.fixture
def lowercase_skill_dir(temp_skills_dir):
    """Create a skill directory with lowercase skill.md."""
    skill_dir = temp_skills_dir / "lowercase-skill"
    skill_dir.mkdir()

    skill_content = """---
name: lowercase_skill
description: A skill with lowercase filename
---

# Lowercase Skill
"""

    skill_file = skill_dir / "skill.md"
    skill_file.write_text(skill_content, encoding="utf-8")

    return skill_dir


def test_skill_initialization():
    """Test Skill initialization."""
    skill = Skill(
        name="test_skill",
        description="Test description",
        content="Test content",
        skill_dir=Path("/tmp/test"),
    )

    assert skill.name == "test_skill"
    assert skill.description == "Test description"
    assert skill.content == "Test content"
    assert skill.skill_dir == Path("/tmp/test")
    assert skill.parameters_schema["type"] == "object"


@pytest.mark.asyncio
async def test_skill_execute():
    """Test Skill execution."""
    skill = Skill(
        name="test_skill",
        description="Test description",
        content="Hello {name}!",
        skill_dir=Path("/tmp/test"),
    )

    context = ToolContext(agent_name="test", session_id="test-session")
    result = await skill.execute({"name": "World"}, context)

    assert result["success"] is True
    assert result["data"] == "Hello World!"
    assert result["skill"] == "test_skill"
    assert "skill_dir" in result


@pytest.mark.asyncio
async def test_skill_execute_missing_parameter():
    """Test Skill execution with missing parameter."""
    skill = Skill(
        name="test_skill",
        description="Test description",
        content="Hello {name}!",
        skill_dir=Path("/tmp/test"),
    )

    context = ToolContext(agent_name="test", session_id="test-session")
    result = await skill.execute({}, context)

    assert result["success"] is False
    assert "Missing parameter" in result["error"]


def test_skill_loader_initialization():
    """Test SkillLoader initialization."""
    loader = SkillLoader()
    assert len(loader.skill_dirs) >= 2
    assert any("minicode/skills" in str(d) for d in loader.skill_dirs)


def test_skill_loader_custom_dirs():
    """Test SkillLoader with custom directories."""
    custom_dirs = ["/custom/path1", "/custom/path2"]
    loader = SkillLoader(skill_dirs=custom_dirs)

    assert len(loader.skill_dirs) == 2
    assert loader.skill_dirs[0] == Path("/custom/path1")
    assert loader.skill_dirs[1] == Path("/custom/path2")


def test_skill_loader_discover_skills(temp_skills_dir, sample_skill_dir):
    """Test discovering skills in directories."""
    loader = SkillLoader(skill_dirs=[str(temp_skills_dir)])
    skill_dirs = loader.discover_skills()

    assert len(skill_dirs) == 1
    assert skill_dirs[0] == sample_skill_dir


def test_skill_loader_discover_multiple_skills(
    temp_skills_dir, sample_skill_dir, lowercase_skill_dir
):
    """Test discovering multiple skills."""
    loader = SkillLoader(skill_dirs=[str(temp_skills_dir)])
    skill_dirs = loader.discover_skills()

    assert len(skill_dirs) == 2
    assert sample_skill_dir in skill_dirs
    assert lowercase_skill_dir in skill_dirs


def test_skill_loader_load_skill(sample_skill_dir):
    """Test loading a skill from directory."""
    loader = SkillLoader()
    skill = loader.load_skill(sample_skill_dir)

    assert skill is not None
    assert skill.name == "test_skill"
    assert skill.description == "A test skill for unit testing"
    assert "Test Skill Content" in skill.content
    assert skill.skill_dir == sample_skill_dir


def test_skill_loader_load_skill_with_parameters(skill_with_parameters):
    """Test loading a skill with parameters schema."""
    loader = SkillLoader()
    skill = loader.load_skill(skill_with_parameters)

    assert skill is not None
    assert skill.name == "param_skill"
    assert skill.parameters_schema["type"] == "object"
    assert "input" in skill.parameters_schema["properties"]
    assert "input" in skill.parameters_schema["required"]


def test_skill_loader_load_invalid_skill(invalid_skill_dir):
    """Test loading an invalid skill (missing required fields)."""
    loader = SkillLoader()
    skill = loader.load_skill(invalid_skill_dir)

    assert skill is None


def test_skill_loader_load_lowercase_skill(lowercase_skill_dir):
    """Test loading a skill with lowercase filename."""
    loader = SkillLoader()
    skill = loader.load_skill(lowercase_skill_dir)

    assert skill is not None
    assert skill.name == "lowercase_skill"


def test_skill_loader_load_nonexistent_dir():
    """Test loading from non-existent directory."""
    loader = SkillLoader()
    skill = loader.load_skill(Path("/nonexistent/path"))

    assert skill is None


def test_skill_loader_load_all_skills(temp_skills_dir, sample_skill_dir, lowercase_skill_dir):
    """Test loading all skills from directories."""
    loader = SkillLoader(skill_dirs=[str(temp_skills_dir)])
    skills = loader.load_all_skills()

    assert len(skills) == 2
    skill_names = [s.name for s in skills]
    assert "test_skill" in skill_names
    assert "lowercase_skill" in skill_names


def test_skill_loader_empty_directory(temp_skills_dir):
    """Test loading from empty directory."""
    loader = SkillLoader(skill_dirs=[str(temp_skills_dir)])
    skills = loader.load_all_skills()

    assert len(skills) == 0


def test_skill_loader_with_env_var(temp_skills_dir, sample_skill_dir, monkeypatch):
    """Test SkillLoader with MINICODE_SKILLS_DIR environment variable."""
    monkeypatch.setenv("MINICODE_SKILLS_DIR", str(temp_skills_dir))

    loader = SkillLoader()
    skill_dirs = loader.discover_skills()

    assert len(skill_dirs) >= 1
    assert sample_skill_dir in skill_dirs


def test_skill_to_openai_format(sample_skill_dir):
    """Test converting skill to OpenAI format."""
    loader = SkillLoader()
    skill = loader.load_skill(sample_skill_dir)

    openai_format = skill.to_openai_format()

    assert openai_format["type"] == "function"
    assert openai_format["function"]["name"] == "test_skill"
    assert openai_format["function"]["description"] == "A test skill for unit testing"
