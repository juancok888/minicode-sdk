"""Tests for agent functionality."""

import pytest

from minicode import Agent
from minicode.llm.base import BaseLLM
from minicode.session.message import Message, ToolContext
from minicode.tools import BaseTool


class MockLLM(BaseLLM):
    """Mock LLM for testing."""

    async def stream(self, messages, tools=None, **kwargs):
        yield {"type": "content", "content": "test response"}
        yield {"type": "done", "finish_reason": "stop"}

    async def generate(self, messages, **kwargs):
        return {"content": "test response", "finish_reason": "stop"}


class MockTool(BaseTool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock"

    @property
    def description(self) -> str:
        return "Mock tool"

    @property
    def parameters_schema(self):
        return {"type": "object", "properties": {}}

    async def execute(self, params, context: ToolContext):
        return {"success": True, "data": "mock"}


@pytest.mark.asyncio
async def test_agent_creation():
    """Test creating an agent."""
    llm = MockLLM()
    agent = Agent(name="test", llm=llm)

    assert agent.name == "test"
    assert agent.llm is llm
    assert len(agent.messages) == 1  # System message
    assert agent.messages[0].role == "system"


@pytest.mark.asyncio
async def test_agent_with_tools():
    """Test agent with tools."""
    llm = MockLLM()
    tool = MockTool()
    agent = Agent(name="test", llm=llm, tools=[tool])

    assert agent.tool_registry.has("mock")
    assert agent.get_tool("mock") is tool


@pytest.mark.asyncio
async def test_agent_add_tool():
    """Test adding tools to agent."""
    llm = MockLLM()
    agent = Agent(name="test", llm=llm)
    tool = MockTool()

    agent.add_tool(tool)
    assert agent.tool_registry.has("mock")


@pytest.mark.asyncio
async def test_agent_stream():
    """Test agent streaming."""
    llm = MockLLM()
    agent = Agent(name="test", llm=llm)

    chunks = []
    async for chunk in agent.stream("Hello"):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert any(c.get("type") == "content" for c in chunks)


@pytest.mark.asyncio
async def test_agent_generate():
    """Test agent non-streaming generation."""
    llm = MockLLM()
    agent = Agent(name="test", llm=llm)

    response = await agent.generate("Hello")
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_agent_reset_session():
    """Test resetting agent session."""
    llm = MockLLM()
    agent = Agent(name="test", llm=llm)

    # Add a message
    await agent.generate("Hello")
    initial_session = agent.session_id
    initial_msg_count = len(agent.messages)

    # Reset
    agent.reset_session()

    assert agent.session_id != initial_session
    assert len(agent.messages) == 1  # Only system message
    assert agent.messages[0].role == "system"


@pytest.mark.asyncio
async def test_agent_custom_prompt():
    """Test agent with custom prompt."""
    llm = MockLLM()
    custom_prompt = "You are a test assistant."
    agent = Agent(name="test", llm=llm, system_prompt=custom_prompt)

    assert agent.messages[0].content == custom_prompt


@pytest.mark.asyncio
async def test_agent_set_system_prompt():
    """Test updating system prompt."""
    llm = MockLLM()
    agent = Agent(name="test", llm=llm)

    new_prompt = "New system prompt"
    agent.set_system_prompt(new_prompt)

    assert agent.messages[0].content == new_prompt
