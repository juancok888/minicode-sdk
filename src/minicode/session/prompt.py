"""Prompt management for agents."""

from typing import Optional


class PromptManager:
    """Manages system prompts and prompt templates for agents."""

    def __init__(self, system_prompt: Optional[str] = None):
        """Initialize prompt manager.

        Args:
            system_prompt: The base system prompt for the agent
        """
        self._system_prompt = system_prompt or self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Get the default system prompt."""
        return "You are a helpful AI assistant."

    @property
    def system_prompt(self) -> str:
        """Get the current system prompt."""
        return self._system_prompt

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
