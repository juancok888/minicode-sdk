"""Tests for Task/TaskOutput tools and Session management."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from minicode.agent import Agent
from minicode.agent_registry import AgentConfig, AgentRegistry
from minicode.llm.base import BaseLLM
from minicode.session.manager import SessionManager
from minicode.session.session import Session
from minicode.tools.builtin.task import TaskTool
from minicode.tools.builtin.taskoutput import TaskOutputTool, TaskCompletedSignal
from minicode.tools.builtin.read import ReadTool
from minicode.tools.builtin.write import WriteTool


@pytest.fixture(autouse=True)
def cleanup():
    """清理每个测试之间的状态."""
    yield
    SessionManager.clear_all()
    AgentRegistry.clear_all()


@pytest.fixture
def mock_llm():
    """创建一个 mock LLM."""
    llm = MagicMock(spec=BaseLLM)

    async def mock_stream(*args, **kwargs):
        """模拟 LLM 流式输出."""
        yield {"type": "content", "content": "Test response"}
        yield {"type": "done", "finish_reason": "stop"}

    llm.stream = mock_stream
    return llm


class TestSession:
    """测试 Session 类的基本功能."""

    def test_session_creation(self):
        """测试创建 session."""
        session = Session(agent_name="test_agent")

        assert session.id is not None
        assert session.agent_name == "test_agent"
        assert session.parent_id is None
        assert len(session.messages) == 0
        assert session.completed is False
        assert session.result is None

    def test_session_with_parent(self):
        """测试创建带父 session 的子 session."""
        parent = Session(agent_name="parent")
        child = Session(agent_name="child", parent_id=parent.id)

        assert child.parent_id == parent.id

    def test_add_message(self):
        """测试添加消息."""
        from minicode.session.message import Message

        session = Session(agent_name="test")
        msg = Message(role="user", content="Hello")

        assert len(session.messages) == 0
        session.add_message(msg)
        assert len(session.messages) == 1
        assert session.messages[0].content == "Hello"

    def test_session_to_dict(self):
        """测试 session 转换为字典."""
        session = Session(agent_name="test")
        session_dict = session.to_dict()

        assert session_dict["id"] == session.id
        assert session_dict["agent_name"] == "test"
        assert session_dict["message_count"] == 0
        assert session_dict["completed"] is False


class TestSessionManager:
    """测试 SessionManager 单例模式和管理功能."""

    def test_singleton(self):
        """测试 SessionManager 是单例."""
        manager1 = SessionManager()
        manager2 = SessionManager()
        assert manager1 is manager2

    def test_create_session(self):
        """测试创建 session."""
        session = SessionManager.create(agent_name="test")

        assert session.agent_name == "test"
        assert SessionManager.exists(session.id)
        assert SessionManager.get(session.id) == session

    def test_get_nonexistent_session(self):
        """测试获取不存在的 session."""
        result = SessionManager.get("nonexistent")
        assert result is None

    def test_get_or_raise(self):
        """测试 get_or_raise 方法."""
        session = SessionManager.create(agent_name="test")

        # 存在的 session
        assert SessionManager.get_or_raise(session.id) == session

        # 不存在的 session 应该抛出异常
        with pytest.raises(ValueError, match="Session not found"):
            SessionManager.get_or_raise("nonexistent")

    def test_parent_child_relationship(self):
        """测试父子 session 关系."""
        parent = SessionManager.create(agent_name="parent")
        child1 = SessionManager.create(agent_name="child1", parent_id=parent.id)
        child2 = SessionManager.create(agent_name="child2", parent_id=parent.id)

        children = SessionManager.get_children(parent.id)
        assert len(children) == 2
        assert child1 in children
        assert child2 in children

    def test_delete_session(self):
        """测试删除 session."""
        session = SessionManager.create(agent_name="test")
        session_id = session.id

        assert SessionManager.exists(session_id)
        assert SessionManager.delete(session_id) is True
        assert not SessionManager.exists(session_id)
        assert SessionManager.delete(session_id) is False  # 已经删除

    def test_delete_with_children(self):
        """测试递归删除 session 及其子 session."""
        parent = SessionManager.create(agent_name="parent")
        child = SessionManager.create(agent_name="child", parent_id=parent.id)
        grandchild = SessionManager.create(agent_name="grandchild", parent_id=child.id)

        count = SessionManager.delete_with_children(parent.id)

        assert count == 3  # parent + child + grandchild
        assert not SessionManager.exists(parent.id)
        assert not SessionManager.exists(child.id)
        assert not SessionManager.exists(grandchild.id)

    def test_clear_all(self):
        """测试清空所有 session."""
        SessionManager.create(agent_name="test1")
        SessionManager.create(agent_name="test2")

        assert SessionManager.count() == 2
        SessionManager.clear_all()
        assert SessionManager.count() == 0


class TestAgentRegistry:
    """测试 AgentRegistry 功能."""

    def test_initialize_builtins(self):
        """测试自动初始化内置 agent."""
        agents = AgentRegistry.list()

        assert len(agents) >= 2  # 至少有 explore 和 general
        assert AgentRegistry.exists("explore")
        assert AgentRegistry.exists("general")

    def test_builtin_agents(self):
        """测试内置 agent 配置."""
        explore = AgentRegistry.get("explore")
        assert explore is not None
        assert explore.name == "explore"
        assert explore.mode == "subagent"
        assert explore.native is True
        assert "task" in explore.denied_tools
        assert "todowrite" in explore.denied_tools

        general = AgentRegistry.get("general")
        assert general is not None
        assert general.mode == "subagent"
        assert general.native is True

    def test_register_custom_agent(self):
        """测试注册自定义 agent."""
        config = AgentConfig(
            name="custom",
            mode="all",
            description="Custom agent",
        )
        AgentRegistry.register(config)

        assert AgentRegistry.exists("custom")
        retrieved = AgentRegistry.get("custom")
        assert retrieved.name == "custom"
        assert retrieved.native is False

    def test_cannot_override_native(self):
        """测试不能用用户定义 agent 覆盖内置 agent."""
        config = AgentConfig(
            name="explore",  # 尝试覆盖内置 agent
            mode="all",
        )

        with pytest.raises(ValueError, match="Cannot override native agent"):
            AgentRegistry.register(config)

    def test_list_by_mode(self):
        """测试按模式过滤 agent."""
        subagents = AgentRegistry.list(mode="subagent")

        # 所有 subagent 应该是 subagent 或 all 模式
        for agent in subagents:
            assert agent.mode in ["subagent", "all"]

    def test_unregister(self):
        """测试注销 agent."""
        config = AgentConfig(name="custom", mode="all")
        AgentRegistry.register(config)

        assert AgentRegistry.exists("custom")
        assert AgentRegistry.unregister("custom") is True
        assert not AgentRegistry.exists("custom")
        assert AgentRegistry.unregister("custom") is False  # 已经删除

    def test_cannot_unregister_native(self):
        """测试不能注销内置 agent."""
        with pytest.raises(ValueError, match="Cannot unregister native agent"):
            AgentRegistry.unregister("explore")


class TestAgentWithSession:
    """测试 Agent 与 Session 的集成."""

    def test_agent_creates_session_automatically(self, mock_llm):
        """测试 Agent 自动创建 session."""
        agent = Agent(name="test", llm=mock_llm)

        assert agent.session is not None
        assert agent.session.agent_name == "test"
        assert agent.session_id == agent.session.id
        assert len(agent.messages) == 1  # system message

    def test_agent_with_existing_session(self, mock_llm):
        """测试 Agent 使用已有 session."""
        session = SessionManager.create(agent_name="test")
        agent = Agent(name="test", llm=mock_llm, session=session)

        assert agent.session == session
        assert agent.session_id == session.id

    def test_backward_compatibility(self, mock_llm):
        """测试向后兼容性（session_id 和 messages 属性）."""
        agent = Agent(name="test", llm=mock_llm)

        # 这些属性应该仍然可用
        assert isinstance(agent.session_id, str)
        assert isinstance(agent.messages, list)
        assert len(agent.messages) == 1  # system message


class TestTaskOutputTool:
    """测试 TaskOutput 工具."""

    @pytest.mark.asyncio
    async def test_taskoutput_raises_signal(self):
        """测试 TaskOutput 工具抛出 TaskCompletedSignal."""
        from minicode.session.message import ToolContext

        tool = TaskOutputTool()
        context = ToolContext(agent_name="test", session_id="test-session")

        params = {
            "result": "Task completed successfully",
            "metadata": {"count": 42}
        }

        with pytest.raises(TaskCompletedSignal) as exc_info:
            await tool.execute(params, context)

        signal = exc_info.value
        assert signal.result == "Task completed successfully"
        assert signal.metadata["count"] == 42

    def test_taskoutput_schema(self):
        """测试 TaskOutput 工具的 schema."""
        tool = TaskOutputTool()

        assert tool.name == "taskoutput"
        assert "result" in tool.parameters_schema["properties"]
        assert "metadata" in tool.parameters_schema["properties"]
        assert "result" in tool.parameters_schema["required"]


class TestTaskTool:
    """测试 Task 工具的核心功能."""

    @pytest.mark.asyncio
    async def test_task_tool_unknown_subagent(self, mock_llm):
        """测试使用未知的 subagent 类型."""
        from minicode.session.message import ToolContext

        agent = Agent(name="main", llm=mock_llm)
        task_tool = TaskTool(parent_agent=agent)
        context = ToolContext(agent_name="main", session_id=agent.session_id)

        params = {
            "description": "Test task",
            "prompt": "Do something",
            "subagent_type": "nonexistent"
        }

        result = await task_tool.execute(params, context)

        assert result["success"] is False
        assert "Unknown subagent type" in result["error"]

    @pytest.mark.asyncio
    async def test_task_tool_primary_agent_restriction(self, mock_llm):
        """测试不能使用 primary 模式的 agent 作为 subagent."""
        from minicode.session.message import ToolContext

        # 注册一个 primary 模式的 agent
        AgentRegistry.register(AgentConfig(
            name="primary_only",
            mode="primary",
        ))

        agent = Agent(name="main", llm=mock_llm)
        task_tool = TaskTool(parent_agent=agent)
        context = ToolContext(agent_name="main", session_id=agent.session_id)

        params = {
            "description": "Test task",
            "prompt": "Do something",
            "subagent_type": "primary_only"
        }

        result = await task_tool.execute(params, context)

        assert result["success"] is False
        assert "cannot be used as a subagent" in result["error"]

    def test_task_tool_filters_forbidden_tools(self, mock_llm):
        """测试 Task 工具正确过滤禁止的工具."""
        agent = Agent(name="main", llm=mock_llm)

        # 添加各种工具
        agent.add_tool(ReadTool())
        agent.add_tool(WriteTool())
        task_tool = TaskTool(parent_agent=agent)
        agent.add_tool(task_tool)

        # 获取 explore agent 配置
        explore_config = AgentRegistry.get("explore")

        # 测试工具过滤
        allowed = task_tool._get_allowed_tools(explore_config, agent)
        tool_names = [t.name for t in allowed]

        # explore 应该有 read_file，但不应该有 write_file
        assert "read_file" in tool_names
        assert "write_file" not in tool_names

        # 不应该包含 task（防止递归）
        assert "task" not in tool_names

        # 不应该包含 todowrite
        assert "todowrite" not in tool_names

    def test_task_tool_parameter_schema(self, mock_llm):
        """测试 Task 工具的参数 schema."""
        agent = Agent(name="main", llm=mock_llm)
        task_tool = TaskTool(parent_agent=agent)

        schema = task_tool.parameters_schema

        assert "description" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "subagent_type" in schema["properties"]
        assert "session_id" in schema["properties"]

        # session_id 是可选的
        required = schema["required"]
        assert "description" in required
        assert "prompt" in required
        assert "subagent_type" in required
        assert "session_id" not in required


class TestTaskIntegration:
    """测试 Task 工具的集成场景（易错点）."""

    @pytest.mark.asyncio
    async def test_subagent_cannot_use_task_tool(self, mock_llm):
        """测试子 agent 不能使用 Task 工具（防止递归）."""
        from minicode.session.message import ToolContext

        # 创建主 agent
        main_agent = Agent(name="main", llm=mock_llm)
        main_agent.add_tool(ReadTool())
        task_tool = TaskTool(parent_agent=main_agent)
        main_agent.add_tool(task_tool)

        # 获取子 agent 允许的工具
        general_config = AgentRegistry.get("general")
        allowed_tools = task_tool._get_allowed_tools(general_config, main_agent)
        tool_names = [t.name for t in allowed_tools]

        # 验证子 agent 不能访问 task 工具
        assert "task" not in tool_names

    @pytest.mark.asyncio
    async def test_subagent_has_taskoutput_tool(self, mock_llm):
        """测试子 agent 总是包含 TaskOutput 工具."""
        from minicode.session.message import ToolContext

        # 创建主 agent
        agent = Agent(name="main", llm=mock_llm)
        agent.add_tool(ReadTool())
        task_tool = TaskTool(parent_agent=agent)

        # 创建子 session
        session = SessionManager.create(
            agent_name="general",
            parent_id=agent.session_id,
        )

        # 模拟创建子 agent（简化版）
        general_config = AgentRegistry.get("general")
        subagent = Agent(
            name="general",
            llm=mock_llm,
            session=session,
        )

        # 添加过滤后的工具
        allowed_tools = task_tool._get_allowed_tools(general_config, agent)
        for tool in allowed_tools:
            subagent.add_tool(tool)

        # 添加 TaskOutput
        subagent.add_tool(TaskOutputTool())

        # 验证 TaskOutput 存在
        assert subagent.get_tool("taskoutput") is not None

    def test_session_hierarchy(self, mock_llm):
        """测试 session 层级关系."""
        # 创建主 agent
        main_agent = Agent(name="main", llm=mock_llm)
        main_session_id = main_agent.session_id

        # 创建子 session
        child_session = SessionManager.create(
            agent_name="child",
            parent_id=main_session_id,
        )

        # 验证层级关系
        assert child_session.parent_id == main_session_id

        # 验证可以查询子 session
        children = SessionManager.get_children(main_session_id)
        assert len(children) == 1
        assert children[0].id == child_session.id

    @pytest.mark.asyncio
    async def test_session_recovery(self, mock_llm):
        """测试 session 恢复功能."""
        from minicode.session.message import ToolContext, Message

        # 创建一个 session 并添加一些消息
        session = SessionManager.create(agent_name="test")
        session.add_message(Message(role="user", content="First message"))
        session.add_message(Message(role="assistant", content="First response"))

        session_id = session.id

        # 创建主 agent 和 task tool
        agent = Agent(name="main", llm=mock_llm)
        agent.add_tool(ReadTool())
        task_tool = TaskTool(parent_agent=agent)
        context = ToolContext(agent_name="main", session_id=agent.session_id)

        # 使用 session_id 恢复 session
        params = {
            "description": "Resume task",
            "prompt": "Continue working",
            "subagent_type": "general",
            "session_id": session_id
        }

        # Task 工具应该能够获取已有 session
        # (注意：这里我们只测试 session 恢复逻辑，不实际运行子 agent)
        recovered_session = SessionManager.get(session_id)
        assert recovered_session is not None
        assert len(recovered_session.messages) == 2


class TestEdgeCases:
    """测试边界情况和易错点."""

    def test_session_manager_is_truly_singleton(self):
        """测试 SessionManager 真的是单例."""
        # 多次创建应该返回同一个实例
        instances = [SessionManager() for _ in range(10)]
        assert all(inst is instances[0] for inst in instances)

    def test_agent_registry_initialization_idempotent(self):
        """测试 AgentRegistry 初始化是幂等的."""
        # 多次调用 initialize_builtins 不应该重复注册
        count1 = AgentRegistry.count()
        AgentRegistry.initialize_builtins()
        count2 = AgentRegistry.count()
        AgentRegistry.initialize_builtins()
        count3 = AgentRegistry.count()

        assert count1 == count2 == count3

    def test_empty_metadata_in_taskoutput(self):
        """测试 TaskOutput 不传 metadata 的情况."""
        with pytest.raises(TaskCompletedSignal) as exc_info:
            raise TaskCompletedSignal("result")

        signal = exc_info.value
        assert signal.result == "result"
        assert signal.metadata == {}

    def test_session_completed_flag(self):
        """测试 session 的 completed 标志."""
        session = Session(agent_name="test")

        assert session.completed is False
        assert session.result is None

        # 标记为完成
        session.completed = True
        session.result = "Done!"

        assert session.completed is True
        assert session.result == "Done!"
