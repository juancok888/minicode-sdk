"""minicode: A Python SDK for building AI agents with LLM, tools, and MCP support.

minicode provides a clean and extensible framework for building AI agents that can:
- Use different LLM providers through a common interface
- Execute tools to interact with the environment
- Connect to MCP (Model Context Protocol) servers
- Load and use skills from Markdown files

Example:
    >>> from minicode import Agent
    >>> from minicode.llm import OpenAILLM
    >>> from minicode.tools import ReadTool, WriteTool
    >>>
    >>> agent = Agent(
    ...     name="assistant",
    ...     llm=OpenAILLM(api_key="your-key"),
    ...     tools=[ReadTool(), WriteTool()],
    ...     prompt="You are a helpful coding assistant."
    ... )
    >>>
    >>> async for chunk in agent.stream("Read the README.md file"):
    ...     print(chunk)
"""

__version__ = "0.1.1"

from minicode.agent import Agent
from minicode.config import add_global_mcp_server, get_global_mcp_servers, MCPConfig
from minicode.llm import BaseLLM, OpenAILLM
from minicode.mcp import MCPClient
from minicode.session import Message, MessageRole, ToolContext
from minicode.skills import Skill, SkillLoader
from minicode.tools import BaseTool, ReadTool, ToolRegistry, WriteTool

__all__ = [
    # Version
    "__version__",
    # Core
    "Agent",
    # Config
    "MCPConfig",
    "get_global_mcp_servers",
    "add_global_mcp_server",
    # LLM
    "BaseLLM",
    "OpenAILLM",
    # Tools
    "BaseTool",
    "ToolRegistry",
    "ReadTool",
    "WriteTool",
    # Session
    "Message",
    "MessageRole",
    "ToolContext",
    # MCP
    "MCPClient",
    # Skills
    "Skill",
    "SkillLoader",
]
