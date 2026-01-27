"""Skill tool for loading and accessing skills.

This tool provides access to skills defined in skill directories.
Skills are discovered from:
- .minicode/skills
- ~/.minicode/skills
- MINICODE_SKILLS_DIR environment variable (if set)
"""

from typing import Any, Dict, List

from minicode.session.message import ToolContext
from minicode.skills.loader import Skill, SkillLoader
from minicode.tools.base import BaseTool


class SkillTool(BaseTool):
    """Tool for executing skills.

    Skills are specialized prompts/instructions loaded from skill directories.
    Each skill is defined by a SKILL.md file with YAML frontmatter containing
    metadata (name, description) and markdown content (instructions).
    """

    def __init__(self, skill_loader: SkillLoader | None = None):
        """Initialize the skill tool.

        Args:
            skill_loader: Optional SkillLoader instance. If None, creates default loader.
        """
        self._skill_loader = skill_loader or SkillLoader()
        self._skills: List[Skill] = []
        self._skills_loaded = False

    def _ensure_skills_loaded(self) -> None:
        """Ensure skills are loaded from disk."""
        if not self._skills_loaded:
            self._skills = self._skill_loader.load_all_skills()
            self._skills_loaded = True

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "skill"

    @property
    def description(self) -> str:
        """Get the tool description with available skills."""
        self._ensure_skills_loaded()

        if not self._skills:
            return (
                "Execute a skill within the main conversation\n\n"
                "<skills_instructions>\n"
                "When users ask you to perform tasks, check if any of the available skills below "
                "can help complete the task more effectively. Skills provide specialized capabilities "
                "and domain knowledge.\n\n"
                "How to use skills:\n"
                "- Invoke skills using this tool with the skill name only (no arguments)\n"
                "- When you invoke a skill, you will see <command-message>The \"{name}\" skill is loading</command-message>\n"
                "- The skill's prompt will expand and provide detailed instructions on how to complete the task\n"
                "- Examples:\n"
                "  - `skill: \"pdf\"` - invoke the pdf skill\n"
                "  - `skill: \"xlsx\"` - invoke the xlsx skill\n"
                "  - `skill: \"ms-office-suite:pdf\"` - invoke using fully qualified name\n\n"
                "Important:\n"
                "- Only use skills listed in <available_skills> below\n"
                "- Do not invoke a skill that is already running\n"
                "- Do not use this tool for built-in CLI commands (like /help, /clear, etc.)\n"
                "</skills_instructions>\n\n"
                "<available_skills>\n\n"
                "</available_skills>\n"
            )

        # Build description with available skills
        skills_list = []
        for skill in self._skills:
            skills_list.append(f"  <skill>")
            skills_list.append(f"    <name>{skill.name}</name>")
            skills_list.append(f"    <description>{skill.description}</description>")
            skills_list.append(f"  </skill>")

        return (
            "Execute a skill within the main conversation\n\n"
            "<skills_instructions>\n"
            "When users ask you to perform tasks, check if any of the available skills below "
            "can help complete the task more effectively. Skills provide specialized capabilities "
            "and domain knowledge.\n\n"
            "How to use skills:\n"
            "- Invoke skills using this tool with the skill name only (no arguments)\n"
            "- When you invoke a skill, you will see <command-message>The \"{name}\" skill is loading</command-message>\n"
            "- The skill's prompt will expand and provide detailed instructions on how to complete the task\n"
            "- Examples:\n"
            "  - `skill: \"pdf\"` - invoke the pdf skill\n"
            "  - `skill: \"xlsx\"` - invoke the xlsx skill\n"
            "  - `skill: \"ms-office-suite:pdf\"` - invoke using fully qualified name\n\n"
            "Important:\n"
            "- Only use skills listed in <available_skills> below\n"
            "- Do not invoke a skill that is already running\n"
            "- Do not use this tool for built-in CLI commands (like /help, /clear, etc.)\n"
            "</skills_instructions>\n\n"
            "<available_skills>\n"
            + "\n".join(skills_list)
            + "\n</available_skills>\n"
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "skill": {
                    "type": "string",
                    "description": 'The skill name (no arguments). E.g., "pdf" or "xlsx"',
                }
            },
            "required": ["skill"],
            "additionalProperties": False,
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute the skill tool.

        Args:
            params: Parameters containing "skill" name
            context: Tool execution context

        Returns:
            Dict with skill content and metadata

        Raises:
            ValueError: If skill not found
        """
        self._ensure_skills_loaded()

        skill_name = params["skill"]

        # Find the skill
        skill = None
        for s in self._skills:
            if s.name == skill_name:
                skill = s
                break

        if skill is None:
            available = ", ".join(s.name for s in self._skills) or "none"
            raise ValueError(f'Skill "{skill_name}" not found. Available skills: {available}')

        # Return the raw markdown content
        output = [
            f"## Skill: {skill.name}",
            "",
            f"**Base directory**: {skill.skill_dir}",
            "",
            skill.content.strip(),
        ]

        return {
            "success": True,
            "data": "\n".join(output),
            "skill_name": skill.name,
            "skill_dir": str(skill.skill_dir),
        }
