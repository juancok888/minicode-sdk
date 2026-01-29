"""Core Agent implementation for minicode SDK."""

import json
import uuid
from typing import Any, AsyncIterator, Dict, List, Literal, Optional, TypedDict, TYPE_CHECKING

from minicode.llm.base import BaseLLM
from minicode.session.message import Message, ToolContext
from minicode.session.prompt import PromptManager
from minicode.tools.base import BaseTool
from minicode.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from minicode.mcp import MCPClient
    from minicode.session.session import Session


AgentMode = Literal["primary", "subagent", "all"]


class MCPServerConfig(TypedDict, total=False):
    """Configuration for an MCP server (internal format).

    Attributes:
        name: Identifier for this server.
        command: Command list to launch stdio-based MCP server (mutually exclusive with url).
        url: URL for HTTP-based MCP server (mutually exclusive with command).
        env: Environment variables for stdio server.
        headers: HTTP headers for HTTP server.

    Note:
        This is the internal format used after parsing Claude Code style config.
        The config file uses Claude Code format with 'command' and 'args' separate,
        which gets converted to a single 'command' list internally.
    """

    name: str
    command: List[str]
    url: str
    env: Dict[str, str]
    headers: Dict[str, str]


class Agent:
    """Core Agent class for building AI agents.

    An agent combines an LLM, tools, and session management to create
    an interactive AI assistant that can use tools to accomplish tasks.
    """

    def __init__(
        self,
        name: str,
        llm: BaseLLM,
        system_prompt: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        mcp_servers: Optional[List[MCPServerConfig]] = None,
        use_global_mcp: bool = True,
        use_agent_instructions: bool = True,
        mode: AgentMode = "primary",
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        auto_confirm_tools: bool = False,
        session: Optional["Session"] = None,
    ):
        """Initialize an Agent.

        Args:
            name: Name identifier for this agent.
            llm: The LLM implementation to use.
            system_prompt: System prompt for the agent.
            tools: List of tools available to the agent.
            mcp_servers: List of MCP server configurations in internal format.
                Each config should contain 'name' and either 'command' (list) or 'url'.
                Example: [{'name': 'memory', 'command': ['npx', '-y', '@modelcontextprotocol/server-memory']}]
            use_global_mcp: If True, also load MCP servers from global config file.
                Global config is loaded from .minicode/mcp.json (project) or
                ~/.minicode/mcp.json (user). Set to False to disable.
            use_agent_instructions: If True, load agent instructions from
                .minicode/AGENT.md (project) or ~/.minicode/AGENT.md (user).
                Can also be controlled via MINICODE_AGENT_INSTRUCTIONS env var.
                Set to False to disable.
            mode: Agent mode - 'primary', 'subagent', or 'all'.
            temperature: Sampling temperature for LLM.
            top_p: Nucleus sampling parameter.
            max_tokens: Maximum tokens to generate.
            auto_confirm_tools: If True, automatically confirm tool executions.
            session: Optional Session instance. If None, creates a new session.
        """
        self.name = name
        self.llm = llm
        self.mode = mode
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.auto_confirm_tools = auto_confirm_tools

        # Initialize prompt manager
        self.prompt_manager = PromptManager(
            system_prompt, use_agent_instructions=use_agent_instructions
        )

        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        if tools:
            self.tool_registry.register_multiple(tools)

        # MCP client (will be initialized if mcp_servers provided)
        self._mcp_client: Optional["MCPClient"] = None
        self._mcp_servers_config = self._build_mcp_config(mcp_servers, use_global_mcp)

        # Session 管理（支持传入已有 session）
        if session:
            self._session = session
        else:
            # 创建新 session
            from minicode.session.manager import SessionManager
            self._session = SessionManager.create(agent_name=name)

        # Add system message
        self._add_system_message()

    @property
    def session_id(self) -> str:
        """获取当前 session ID（向后兼容）.

        Returns:
            Session ID
        """
        return self._session.id

    @property
    def messages(self) -> List[Message]:
        """获取当前 session 的消息列表（向后兼容）.

        Returns:
            消息列表
        """
        return self._session.messages

    @property
    def session(self) -> "Session":
        """获取当前 session 实例.

        Returns:
            Session 实例
        """
        return self._session

    def _add_system_message(self) -> None:
        """Add the system message to the conversation."""
        system_prompt = self.prompt_manager.system_prompt
        self._session.add_message(Message(role="system", content=system_prompt))

    def _build_mcp_config(
        self,
        mcp_servers: Optional[List[MCPServerConfig]],
        use_global_mcp: bool,
    ) -> Optional[List[MCPServerConfig]]:
        """Build the combined MCP server configuration.

        Args:
            mcp_servers: Explicit MCP server configurations.
            use_global_mcp: Whether to include global MCP configurations.

        Returns:
            Combined list of MCP server configurations, or None if empty.
        """
        configs: List[MCPServerConfig] = []

        # Load global config first (lower precedence)
        if use_global_mcp:
            from minicode.config import get_global_mcp_servers

            global_servers = get_global_mcp_servers()
            for server in global_servers:
                # Cast to MCPServerConfig (it's compatible)
                configs.append(server)  # type: ignore

        # Add explicit configs (higher precedence, may override global)
        if mcp_servers:
            # Track names to avoid duplicates
            existing_names = {c.get("name") for c in configs}
            for server in mcp_servers:
                name = server.get("name")
                if name in existing_names:
                    # Remove existing config with same name (explicit overrides global)
                    configs = [c for c in configs if c.get("name") != name]
                configs.append(server)

        return configs if configs else None

    async def initialize_mcp(self) -> None:
        """Initialize MCP servers and register their tools.

        This method should be called before using the agent if mcp_servers
        were configured. It connects to all configured MCP servers and
        registers their tools with the agent.

        Raises:
            ValueError: If MCP server configuration is invalid.
        """
        if not self._mcp_servers_config:
            return

        from minicode.mcp import MCPClient

        self._mcp_client = MCPClient()

        for server_config in self._mcp_servers_config:
            name = server_config.get("name")
            if not name:
                raise ValueError("MCP server config must include 'name'")

            command = server_config.get("command")
            url = server_config.get("url")
            env = server_config.get("env")
            headers = server_config.get("headers")

            await self._mcp_client.add_server(
                name=name,
                command=command,
                url=url,
                env=env,
                headers=headers,
            )

        # Register MCP tools
        mcp_tools = self._mcp_client.get_tools()
        if mcp_tools:
            self.tool_registry.register_multiple(mcp_tools)

    async def cleanup_mcp(self) -> None:
        """Disconnect from all MCP servers.

        This method should be called when the agent is no longer needed
        to properly clean up MCP server connections.
        """
        if self._mcp_client:
            await self._mcp_client.disconnect_all()
            self._mcp_client = None

    async def __aenter__(self) -> "Agent":
        """Async context manager entry - initializes MCP servers."""
        await self.initialize_mcp()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - cleans up MCP servers."""
        await self.cleanup_mcp()

    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the agent.

        Args:
            tool: The tool to add
        """
        self.tool_registry.register(tool)

    def add_tools(self, tools: List[BaseTool]) -> None:
        """Add multiple tools to the agent.

        Args:
            tools: List of tools to add
        """
        self.tool_registry.register_multiple(tools)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name.

        Args:
            name: Name of the tool

        Returns:
            The tool if found, None otherwise
        """
        return self.tool_registry.get(name)

    def create_context(self, metadata: Optional[Dict[str, Any]] = None) -> ToolContext:
        """Create a tool execution context.

        Args:
            metadata: Optional metadata to include in the context

        Returns:
            A ToolContext instance
        """
        ctx_metadata = metadata.copy() if metadata else {}
        ctx_metadata["_agent"] = self  # Store agent reference for tools that need it
        return ToolContext(
            agent_name=self.name,
            session_id=self.session_id,
            metadata=ctx_metadata,
        )

    async def _execute_tool(
        self,
        tool_name: str,
        tool_params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute a tool call.

        Args:
            tool_name: Name of the tool to execute
            tool_params: Parameters for the tool
            context: Tool execution context

        Returns:
            The result of the tool execution
        """
        tool = self.get_tool(tool_name)

        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found",
            }

        # Check if confirmation is needed
        if not self.auto_confirm_tools and tool.requires_confirmation(tool_params):
            # TODO: Implement user confirmation prompt
            # In a production implementation, this would prompt the user for confirmation
            # For now, we proceed automatically. Set auto_confirm_tools=True to skip this check.
            pass

        try:
            result = await tool.execute(tool_params, context)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
            }

    async def stream(
        self,
        message: str,
        max_iterations: int = 10,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream a conversation with the agent.

        Args:
            message: The user message to send
            max_iterations: Maximum number of tool-calling iterations

        Yields:
            Chunks of the agent's response
        """
        # Wrap user message with agent instructions (only for the latest message)
        wrapped_message = self.prompt_manager.wrap_user_message(message)
        self._session.add_message(Message(role="user", content=wrapped_message))

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            # Prepare messages for LLM
            messages_dict = [msg.to_dict() for msg in self.messages]

            # Get tools in OpenAI format
            tools = None
            if len(self.tool_registry) > 0:
                tools = self.tool_registry.to_openai_format()

            # Stream from LLM
            assistant_message = Message(role="assistant")
            tool_calls: List[Dict[str, Any]] = []
            content_parts: List[str] = []

            async for chunk in self.llm.stream(
                messages=messages_dict,
                tools=tools,
                temperature=self.temperature,
                top_p=self.top_p,
                max_tokens=self.max_tokens,
            ):
                chunk_type = chunk.get("type")

                if chunk_type == "content":
                    content = chunk.get("content", "")
                    content_parts.append(content)
                    yield {
                        "type": "content",
                        "content": content,
                    }

                elif chunk_type == "tool_call":
                    tool_call = chunk.get("tool_call")
                    if tool_call:
                        tool_calls.append(tool_call)
                        yield {
                            "type": "tool_call",
                            "tool_call": tool_call,
                        }

                elif chunk_type == "done":
                    finish_reason = chunk.get("finish_reason")

                    # Save assistant message
                    if content_parts:
                        assistant_message.content = "".join(content_parts)
                    if tool_calls:
                        assistant_message.tool_calls = tool_calls

                    self._session.add_message(assistant_message)

                    # If no tool calls, we're done
                    if not tool_calls:
                        yield {
                            "type": "done",
                            "finish_reason": finish_reason,
                        }
                        return

                    # Execute tool calls
                    context = self.create_context()

                    for tool_call in tool_calls:
                        function = tool_call.get("function", {})
                        tool_name = function.get("name", "")
                        tool_id = tool_call.get(
                            "id", f"{tool_name}_{uuid.uuid4().hex[:6]}"
                        )
                        tool_params = function.get("arguments", {})

                        # Execute the tool
                        result = await self._execute_tool(
                            tool_name,
                            tool_params,
                            context,
                        )

                        # Add tool result message
                        tool_result_msg = Message(
                            role="tool",
                            content=json.dumps(result),
                            tool_call_id=tool_id,
                            tool_name=tool_name,
                        )
                        self._session.add_message(tool_result_msg)

                        yield {
                            "type": "tool_result",
                            "tool_name": tool_name,
                            "result": result,
                        }

                    # Continue the loop to get the next response
                    break

        # Max iterations reached
        yield {
            "type": "error",
            "error": f"Maximum iterations ({max_iterations}) reached",
        }

    async def generate(self, message: str) -> str:
        """Generate a complete response (non-streaming).

        Args:
            message: The user message to send

        Returns:
            The complete response text
        """
        response_parts: List[str] = []

        async for chunk in self.stream(message):
            if chunk.get("type") == "content":
                response_parts.append(chunk.get("content", ""))

        return "".join(response_parts)

    def reset_session(self) -> None:
        """Reset the agent's session.

        Clears all messages except the system message and generates a new session.
        """
        from minicode.session.manager import SessionManager
        # 创建新 session
        self._session = SessionManager.create(agent_name=self.name)
        self._add_system_message()

    def get_messages(self) -> List[Message]:
        """Get all messages in the current session.

        Returns:
            List of messages
        """
        return self._session.messages.copy()

    def set_system_prompt(self, prompt: str) -> None:
        """Update the system prompt.

        Args:
            prompt: The new system prompt
        """
        self.prompt_manager.set_system_prompt(prompt)

        # Update the system message
        messages = self._session.messages
        if messages and messages[0].role == "system":
            messages[0].content = prompt
        else:
            messages.insert(0, Message(role="system", content=prompt))
