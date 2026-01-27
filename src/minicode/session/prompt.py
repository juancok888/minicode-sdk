"""Prompt management for agents."""

from typing import Optional

from minicode.config import (
    get_agent_instructions,
    is_agent_instructions_enabled,
    AgentInstructionsConfig,
)


class PromptManager:
    """Manages system prompts and prompt templates for agents."""

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        use_agent_instructions: bool = True,
    ):
        """Initialize prompt manager.

        Args:
            system_prompt: The base system prompt for the agent.
            use_agent_instructions: If True, load and inject agent instructions
                from .minicode/AGENT.md (project) or ~/.minicode/AGENT.md (user).
                Can also be controlled via MINICODE_AGENT_INSTRUCTIONS env var.
        """
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._use_agent_instructions = use_agent_instructions
        self._agent_instructions: Optional[str] = None
        self._instructions_source: Optional[str] = None

        if use_agent_instructions and is_agent_instructions_enabled():
            self._load_agent_instructions()

    def _default_system_prompt(self) -> str:
        """Get the default system prompt."""
        return "You are a helpful AI assistant."

    def _load_agent_instructions(self) -> None:
        """Load agent instructions from config files."""
        config = AgentInstructionsConfig()
        self._agent_instructions = config.get_instructions()
        source_path = config.get_source_path()
        if source_path:
            self._instructions_source = str(source_path)

    @property
    def system_prompt(self) -> str:
        """Get the current system prompt."""
        return self._system_prompt

    @property
    def agent_instructions(self) -> Optional[str]:
        """Get the agent instructions content."""
        return self._agent_instructions

    @property
    def instructions_source(self) -> Optional[str]:
        """Get the source path of the agent instructions."""
        return self._instructions_source

    def set_system_prompt(self, prompt: str) -> None:
        """Set a new system prompt.

        Args:
            prompt: The new system prompt
        """
        self._system_prompt = prompt

    def format_prompt(self, **kwargs: str) -> str:
        """Format the system prompt with variables.

        Args:
            **kwargs: Variables to format the prompt with

        Returns:
            The formatted system prompt
        """
        try:
            return self._system_prompt.format(**kwargs)
        except KeyError:
            # If formatting fails, return the original prompt
            return self._system_prompt

    def wrap_user_message(self, message: str) -> str:
        """Wrap user message with agent instructions if available.

        This method injects agent instructions into the user message using
        XML-style tags. Should only be called for the latest user message
        to avoid redundant injection.

        Args:
            message: The original user message.

        Returns:
            The wrapped message with agent instructions, or original message
            if no instructions are available.
        """
        if not self._agent_instructions:
            return message

        return f"""<agent-instructions>
The following are user-defined agent instructions that should guide your behavior.
Source: {self._instructions_source or "unknown"}

{self._agent_instructions}
</agent-instructions>

{message}"""
