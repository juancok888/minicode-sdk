"""Tool registry for managing available tools."""

from typing import Any, Dict, List, Optional

from minicode.tools.base import BaseTool


class ToolRegistry:
    """Registry for managing and accessing tools.

    The registry maintains a collection of tools and provides methods
    to register, retrieve, and list tools.
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry.

        Args:
            tool: The tool to register

        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")

        self._tools[tool.name] = tool

    def register_multiple(self, tools: List[BaseTool]) -> None:
        """Register multiple tools at once.

        Args:
            tools: List of tools to register
        """
        for tool in tools:
            self.register(tool)

    def unregister(self, name: str) -> None:
        """Unregister a tool from the registry.

        Args:
            name: Name of the tool to unregister

        Raises:
            KeyError: If no tool with that name is registered
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered")

        del self._tools[name]

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name.

        Args:
            name: Name of the tool to retrieve

        Returns:
            The tool if found, None otherwise
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: Name of the tool to check

        Returns:
            True if the tool is registered, False otherwise
        """
        return name in self._tools

    def list_tools(self) -> List[str]:
        """Get a list of all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_all(self) -> List[BaseTool]:
        """Get all registered tools.

        Returns:
            List of all registered tools
        """
        return list(self._tools.values())

    def to_openai_format(self) -> List[Dict[str, Any]]:
        """Convert all registered tools to OpenAI function calling format.

        Returns:
            List of tool definitions in OpenAI format
        """
        return [tool.to_openai_format() for tool in self._tools.values()]

    def clear(self) -> None:
        """Remove all registered tools."""
        self._tools.clear()

    def __len__(self) -> int:
        """Get the number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered using 'in' operator."""
        return name in self._tools
