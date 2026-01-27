"""Base tool abstraction for minicode SDK."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from minicode.session.message import ToolContext


class BaseTool(ABC):
    """Abstract base class for tool implementations.

    Tools are functions that agents can call to perform specific tasks.
    Each tool must define its name, description, parameters schema, and execution logic.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the tool name.

        This should be a unique identifier for the tool (e.g., 'read_file', 'web_search').

        Returns:
            The tool name
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Get the tool description.

        This description helps the LLM understand when and how to use the tool.
        Be clear and specific about what the tool does.

        Returns:
            A clear description of the tool's purpose
        """
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the JSON Schema for the tool's parameters.

        This schema defines the expected parameters for the tool.
        It should follow JSON Schema specification.

        Returns:
            A JSON Schema dictionary describing the parameters

        Example:
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding",
                        "default": "utf-8"
                    }
                },
                "required": ["path"]
            }
        """
        pass

    @abstractmethod
    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute the tool with given parameters.

        Args:
            params: The parameters for this tool execution (validated against schema)
            context: The execution context containing agent info and metadata

        Returns:
            A dictionary containing the result of the tool execution.
            Should typically include:
            - 'success': bool - whether the operation succeeded
            - 'data': Any - the main result data
            - 'error': str - error message if failed

        Example:
            {
                "success": True,
                "data": "File contents here...",
            }

            or on error:

            {
                "success": False,
                "error": "File not found: /path/to/file"
            }
        """
        pass

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert tool definition to OpenAI function calling format.

        Returns:
            A dictionary in OpenAI's function calling format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }

    def requires_confirmation(self, params: Dict[str, Any]) -> bool:
        """Check if this tool execution requires user confirmation.

        Override this method to implement custom confirmation logic.

        Args:
            params: The parameters that will be used

        Returns:
            True if user confirmation is required, False otherwise
        """
        return False

    def get_confirmation_message(self, params: Dict[str, Any]) -> str:
        """Get the message to show when asking for user confirmation.

        Args:
            params: The parameters that will be used

        Returns:
            A message explaining what the tool will do
        """
        return f"Execute {self.name} with parameters: {params}"
