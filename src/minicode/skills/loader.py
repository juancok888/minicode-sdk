"""Skills loader for minicode SDK."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool


class Skill(BaseTool):
    """Represents a skill loaded from a skill directory.

    Skills are tools defined in skill directories with a SKILL.md file
    that contains YAML metadata and Markdown content.
    """

    def __init__(
        self,
        name: str,
        description: str,
        content: str,
        skill_dir: Path,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a skill.

        Args:
            name: Name of the skill
            description: Description of what the skill does
            content: The skill content (prompt/instructions)
            skill_dir: Path to the skill directory
            parameters: Optional JSON Schema for parameters
        """
        self._name = name
        self._description = description
        self._content = content
        self._skill_dir = skill_dir
        self._parameters = parameters or {
            "type": "object",
            "properties": {},
        }

    @property
    def name(self) -> str:
        """Get the skill name."""
        return self._name

    @property
    def description(self) -> str:
        """Get the skill description."""
        return self._description

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return self._parameters

    @property
    def content(self) -> str:
        """Get the skill content."""
        return self._content

    @property
    def skill_dir(self) -> Path:
        """Get the skill directory path."""
        return self._skill_dir

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute the skill.

        For skills, execution typically returns the skill content
        with parameters interpolated.
        """
        try:
            # Format the content with parameters
            formatted_content = self._content.format(**params)

            return {
                "success": True,
                "data": formatted_content,
                "skill": self._name,
                "skill_dir": str(self._skill_dir),
            }
        except KeyError as e:
            return {
                "success": False,
                "error": f"Missing parameter: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute skill: {str(e)}",
            }


class SkillLoader:
    """Loader for discovering and loading skills from skill directories."""

    def __init__(self, skill_dirs: Optional[List[str]] = None):
        """Initialize skill loader.

        Args:
            skill_dirs: List of directories to search for skills.
                       If None, uses default locations (.minicode/skills, ~/.minicode/skills)
                       and MINICODE_SKILLS_DIR environment variable if set.
        """
        if skill_dirs is None:
            skill_dirs = [
                ".minicode/skills",
                os.path.expanduser("~/.minicode/skills"),
            ]
            # Add environment variable path if set
            env_skills_dir = os.environ.get("MINICODE_SKILLS_DIR")
            if env_skills_dir:
                skill_dirs.append(env_skills_dir)
        self.skill_dirs = [Path(d) for d in skill_dirs]

    def discover_skills(self) -> List[Path]:
        """Discover all skill directories in the configured directories.

        Returns:
            List of paths to skill directories (containing SKILL.md files)
        """
        skill_dirs: List[Path] = []

        for base_dir in self.skill_dirs:
            if not base_dir.exists() or not base_dir.is_dir():
                continue

            # Find all directories containing SKILL.md (case-insensitive)
            for item in base_dir.iterdir():
                if not item.is_dir():
                    continue

                # Check for SKILL.md (case-insensitive)
                skill_file = None
                for filename in ["SKILL.md", "skill.md", "Skill.md"]:
                    candidate = item / filename
                    if candidate.exists() and candidate.is_file():
                        skill_file = candidate
                        break

                if skill_file:
                    skill_dirs.append(item)

        return skill_dirs

    def load_skill(self, skill_dir: Path) -> Optional[Skill]:
        """Load a skill from a skill directory.

        Args:
            skill_dir: Path to the skill directory

        Returns:
            A Skill instance, or None if loading failed
        """
        try:
            # Find SKILL.md file (case-insensitive)
            skill_file = None
            for filename in ["SKILL.md", "skill.md", "Skill.md"]:
                candidate = skill_dir / filename
                if candidate.exists() and candidate.is_file():
                    skill_file = candidate
                    break

            if not skill_file:
                return None

            content = skill_file.read_text(encoding="utf-8")

            # Parse YAML frontmatter and Markdown content
            # Expected format:
            # ---
            # name: skill_name
            # description: Skill description
            # ---
            # Markdown content here

            # Extract YAML frontmatter
            yaml_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)

            if not yaml_match:
                return None

            yaml_content = yaml_match.group(1)
            markdown_content = yaml_match.group(2).strip()

            # Parse YAML metadata
            try:
                metadata = yaml.safe_load(yaml_content)
            except yaml.YAMLError:
                return None

            # Validate required fields
            if not isinstance(metadata, dict):
                return None

            name = metadata.get("name")
            description = metadata.get("description")

            if not name or not description:
                return None

            # Get optional parameters schema
            parameters = metadata.get("parameters")

            return Skill(
                name=name,
                description=description,
                content=markdown_content,
                skill_dir=skill_dir,
                parameters=parameters,
            )

        except Exception:
            return None

    def load_all_skills(self) -> List[Skill]:
        """Discover and load all skills.

        Returns:
            List of loaded Skill instances
        """
        skills: List[Skill] = []
        skill_dirs = self.discover_skills()

        for skill_dir in skill_dirs:
            skill = self.load_skill(skill_dir)
            if skill:
                skills.append(skill)

        return skills
