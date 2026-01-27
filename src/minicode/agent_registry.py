"""Agent registry for managing agent configurations."""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


AgentMode = Literal["primary", "subagent", "all"]


class AgentConfig(BaseModel):
    """Agent 配置定义.

    定义了 agent 的元数据、系统 prompt、权限规则等。

    Attributes:
        name: Agent 唯一标识符
        description: Agent 描述（用于 Task 工具的 prompt）
        mode: Agent 模式（primary/subagent/all）
        native: 是否为内置 agent
        prompt: 系统 prompt
        temperature: 温度参数覆盖
        top_p: Top-p 参数覆盖
        max_tokens: Max tokens 覆盖
        model: 模型覆盖
        allowed_tools: 允许的工具列表
        denied_tools: 禁止的工具列表
    """

    name: str = Field(description="Unique agent identifier")
    description: Optional[str] = Field(default=None, description="Agent description for Task tool")
    mode: AgentMode = Field(default="all", description="Agent mode")
    native: bool = Field(default=False, description="Whether this is a built-in agent")

    # Prompt 配置
    prompt: Optional[str] = Field(default=None, description="System prompt for this agent")

    # LLM 参数（可选覆盖）
    temperature: Optional[float] = Field(default=None, description="Temperature override")
    top_p: Optional[float] = Field(default=None, description="Top-p override")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens override")
    model: Optional[str] = Field(default=None, description="Model override (e.g., 'gpt-4o-mini')")

    # 工具配置
    allowed_tools: Optional[List[str]] = Field(
        default=None,
        description="List of allowed tool names. If None, all tools are allowed except denied ones"
    )
    denied_tools: List[str] = Field(
        default_factory=list,
        description="List of denied tool names"
    )

    class Config:
        """Pydantic 配置."""
        use_enum_values = True


# 内置 agent 的 prompt 定义
EXPLORE_PROMPT = """You are a file search specialist. You excel at thoroughly navigating and exploring codebases.

Your strengths:
- Rapidly finding files using glob patterns
- Searching code and text with powerful regex patterns
- Reading and analyzing file contents

Guidelines:
- Use Glob for broad file pattern matching
- Use Grep for searching file contents with regex
- Use Read when you know the specific file path
- Adapt your search approach based on the thoroughness level specified
- Return file paths as absolute paths in your final response
- Do not create any files or modify system state
- When done, call TaskOutput with your findings

Complete the user's search request efficiently and report your findings clearly."""


GENERAL_PROMPT = """You are a general-purpose AI assistant specialized in complex research and multi-step tasks.

Your strengths:
- Breaking down complex problems into manageable steps
- Conducting thorough research using available tools
- Synthesizing information from multiple sources
- Providing clear and actionable recommendations

Guidelines:
- Use available tools effectively to gather information
- Think step-by-step through complex problems
- Provide clear reasoning for your conclusions
- When done, call TaskOutput with your complete findings

Complete the user's request thoroughly and return your results clearly."""


class AgentRegistry:
    """全局 agent 注册表.

    管理所有 agent 配置（内置 + 用户自定义）。

    Note:
        AgentRegistry 使用类方法，无需实例化。
        首次访问时会自动初始化内置 agent。
    """

    _agents: Dict[str, AgentConfig] = {}
    _initialized: bool = False

    @classmethod
    def initialize_builtins(cls) -> None:
        """注册所有内置 agent.

        这个方法在第一次访问 registry 时自动调用。
        内置 agent 包括：
        - explore: 代码库探索专家
        - general: 通用任务处理 agent
        """
        if cls._initialized:
            return

        # Explore agent - 用于代码库探索
        cls.register(AgentConfig(
            name="explore",
            mode="subagent",
            native=True,
            description=(
                "Fast agent specialized for exploring codebases. Use this when you need to "
                "quickly find files by patterns (eg. 'src/components/**/*.tsx'), search code "
                "for keywords (eg. 'API endpoints'), or answer questions about the codebase "
                "(eg. 'how do API endpoints work?'). When calling this agent, specify the "
                "desired thoroughness level: 'quick' for basic searches, 'medium' for moderate "
                "exploration, or 'very thorough' for comprehensive analysis."
            ),
            prompt=EXPLORE_PROMPT,
            allowed_tools=["read_file", "glob", "grep", "bash", "taskoutput"],
            denied_tools=["write_file", "edit", "todowrite", "todoread", "task"],
        ))

        # General-purpose agent
        cls.register(AgentConfig(
            name="general",
            mode="subagent",
            native=True,
            description=(
                "General-purpose agent for researching complex questions and executing "
                "multi-step tasks. Use this agent to execute multiple units of work in parallel."
            ),
            prompt=GENERAL_PROMPT,
            denied_tools=["todowrite", "todoread", "task"],
        ))

        cls._initialized = True

    @classmethod
    def register(cls, config: AgentConfig) -> None:
        """注册一个 agent 配置.

        Args:
            config: Agent 配置

        Raises:
            ValueError: 如果尝试用用户定义的 agent 覆盖内置 agent

        Example:
            >>> config = AgentConfig(name="my_agent", mode="all")
            >>> AgentRegistry.register(config)
        """
        # 只有在注册非 native agent 时才需要确保内置已注册
        if not config.native:
            cls.initialize_builtins()

        if config.name in cls._agents:
            # 允许覆盖非 native agent
            existing = cls._agents[config.name]
            if existing.native and not config.native:
                raise ValueError(
                    f"Cannot override native agent '{config.name}' with user-defined agent"
                )

        cls._agents[config.name] = config

    @classmethod
    def get(cls, name: str) -> Optional[AgentConfig]:
        """获取 agent 配置.

        Args:
            name: Agent 名称

        Returns:
            AgentConfig 实例，如果不存在则返回 None

        Example:
            >>> config = AgentRegistry.get("explore")
            >>> if config:
            ...     print(config.description)
        """
        cls.initialize_builtins()
        return cls._agents.get(name)

    @classmethod
    def get_or_raise(cls, name: str) -> AgentConfig:
        """获取 agent 配置，如果不存在则抛出异常.

        Args:
            name: Agent 名称

        Returns:
            AgentConfig 实例

        Raises:
            ValueError: 如果 agent 不存在

        Example:
            >>> config = AgentRegistry.get_or_raise("explore")
            >>> print(config.description)
        """
        config = cls.get(name)
        if config is None:
            raise ValueError(f"Agent not found: {name}")
        return config

    @classmethod
    def list(
        cls,
        mode: Optional[AgentMode] = None,
        include_native: bool = True,
    ) -> List[AgentConfig]:
        """列出所有 agent 配置.

        Args:
            mode: 过滤指定模式的 agent (primary/subagent/all)
            include_native: 是否包含内置 agent

        Returns:
            AgentConfig 列表

        Example:
            >>> subagents = AgentRegistry.list(mode="subagent")
            >>> for agent in subagents:
            ...     print(agent.name)
        """
        cls.initialize_builtins()
        agents = list(cls._agents.values())

        if not include_native:
            agents = [a for a in agents if not a.native]

        if mode:
            agents = [a for a in agents if a.mode == mode or a.mode == "all"]

        return agents

    @classmethod
    def exists(cls, name: str) -> bool:
        """检查 agent 是否存在.

        Args:
            name: Agent 名称

        Returns:
            如果存在返回 True

        Example:
            >>> if AgentRegistry.exists("explore"):
            ...     print("Explore agent is available")
        """
        cls.initialize_builtins()
        return name in cls._agents

    @classmethod
    def unregister(cls, name: str) -> bool:
        """注销一个 agent.

        Args:
            name: Agent 名称

        Returns:
            如果成功注销返回 True，如果 agent 不存在返回 False

        Raises:
            ValueError: 如果尝试注销内置 agent

        Example:
            >>> AgentRegistry.unregister("my_custom_agent")
        """
        cls.initialize_builtins()  # 确保内置 agent 已注册

        if name in cls._agents:
            if cls._agents[name].native:
                raise ValueError(f"Cannot unregister native agent: {name}")
            del cls._agents[name]
            return True
        return False

    @classmethod
    def clear_user_agents(cls) -> None:
        """清除所有用户自定义 agent（保留内置）.

        Example:
            >>> AgentRegistry.clear_user_agents()
            >>> # Only native agents remain
        """
        cls._agents = {k: v for k, v in cls._agents.items() if v.native}

    @classmethod
    def clear_all(cls) -> None:
        """清除所有 agent（包括内置，用于测试）.

        Warning:
            这会删除所有 agent，包括内置 agent。
            仅在测试时使用。

        Example:
            >>> AgentRegistry.clear_all()
            >>> assert len(AgentRegistry.list()) == 0
        """
        cls._agents.clear()
        cls._initialized = False

    @classmethod
    def count(cls) -> int:
        """获取当前 agent 总数.

        Returns:
            Agent 总数

        Example:
            >>> count = AgentRegistry.count()
            >>> print(f"Total agents: {count}")
        """
        cls.initialize_builtins()
        return len(cls._agents)
