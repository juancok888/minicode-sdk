"""AskUserQuestion tool for requesting user input during execution."""

import asyncio
from typing import Any, Callable, Dict, Optional

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool


class AskUserQuestionTool(BaseTool):
    """Tool for asking questions to the user during agent execution.

    This tool allows agents to request clarification or additional information
    from users when needed. Supports both callback-based and CLI-based interaction.
    """

    def __init__(
        self,
        question_callback: Optional[Callable[[str], Any]] = None,
        default_timeout: Optional[float] = None,
    ):
        """Initialize AskUserQuestion tool.

        Args:
            question_callback: Optional async function to handle questions.
                             Signature: async def callback(question: str) -> str
                             If None, uses standard input (CLI mode).
            default_timeout: Default timeout in seconds for waiting for answers.
                           None means no timeout (default).
        """
        self._question_callback = question_callback
        self._default_timeout = default_timeout

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "ask_user_question"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return """Ask a question to the user and wait for their answer.

Usage notes:
- Use this tool when you need clarification or additional information
- Supports multi-round conversations - you can ask follow-up questions
- Can specify a default answer to use if user doesn't respond
- Timeout can be configured (default: no timeout)
- User's answer will be returned for the agent to process

When to use:
- Clarifying ambiguous requirements
- Asking for preferences or choices
- Requesting additional information not available in context
- Confirming actions before execution

Example questions:
- "Which API version should I use: v1 or v2?"
- "What should be the default timeout value?"
- "Should I create a backup before modifying the file?"
"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user",
                },
                "default_answer": {
                    "type": "string",
                    "description": "Optional default answer if user doesn't respond or times out",
                },
                "timeout": {
                    "type": "number",
                    "description": "Optional timeout in seconds to wait for answer. None means no timeout.",
                },
            },
            "required": ["question"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute question asking.

        Args:
            params: Parameters including:
                - question: The question to ask
                - default_answer: Optional default answer
                - timeout: Optional timeout in seconds
            context: Tool execution context

        Returns:
            Dictionary containing:
                - success: Whether question was answered
                - question: The question asked
                - answer: User's answer (or default if timed out)
                - timed_out: Whether the question timed out
                - used_default: Whether default answer was used
        """
        question = params.get("question")
        if not question:
            return {
                "success": False,
                "error": "question parameter is required",
            }

        default_answer = params.get("default_answer")
        timeout = params.get("timeout", self._default_timeout)

        try:
            # Get answer from user
            if self._question_callback:
                # Use callback function
                if timeout is not None:
                    answer = await asyncio.wait_for(
                        self._ensure_coroutine(self._question_callback(question)),
                        timeout=timeout,
                    )
                else:
                    answer = await self._ensure_coroutine(
                        self._question_callback(question)
                    )
            else:
                # Use standard input in executor to avoid blocking event loop
                loop = asyncio.get_event_loop()
                print(f"\n🤔 Question: {question}")

                if default_answer:
                    print(f"   (Default: {default_answer})")

                if timeout is not None:
                    print(f"   (Timeout: {timeout}s)")

                input_prompt = "Your answer: "

                if timeout is not None:
                    answer = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: input(input_prompt)),
                        timeout=timeout,
                    )
                else:
                    answer = await loop.run_in_executor(
                        None, lambda: input(input_prompt)
                    )

            # User provided answer
            return {
                "success": True,
                "question": question,
                "answer": answer.strip() if answer else "",
                "timed_out": False,
                "used_default": False,
            }

        except asyncio.TimeoutError:
            # Handle timeout
            if default_answer:
                # Use default answer
                return {
                    "success": True,
                    "question": question,
                    "answer": default_answer,
                    "timed_out": True,
                    "used_default": True,
                    "message": f"User did not respond within {timeout}s, using default answer: {default_answer}",
                }
            else:
                # No default answer, inform that user didn't respond
                return {
                    "success": True,
                    "question": question,
                    "answer": "",
                    "timed_out": True,
                    "used_default": False,
                    "message": f"User did not respond within {timeout}s and no default answer was provided.",
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get user answer: {str(e)}",
                "question": question,
            }

    async def _ensure_coroutine(self, obj):
        """Ensure the object is a coroutine, await if needed.

        Args:
            obj: Either a coroutine or regular value

        Returns:
            The awaited value
        """
        if asyncio.iscoroutine(obj):
            return await obj
        return obj
