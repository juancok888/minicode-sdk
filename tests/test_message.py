"""Tests for message types and context."""

import pytest

from minicode.session.message import Message, ToolContext


def test_message_creation():
    """Test creating a message."""
    msg = Message(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


def test_message_to_dict():
    """Test converting message to dictionary."""
    msg = Message(role="assistant", content="Hi there")
    d = msg.to_dict()
    assert d["role"] == "assistant"
    assert d["content"] == "Hi there"


def test_message_with_tool_call():
    """Test message with tool call."""
    tool_calls = [{"id": "1", "function": {"name": "test"}}]
    msg = Message(role="assistant", tool_calls=tool_calls)
    d = msg.to_dict()
    assert d["tool_calls"] == tool_calls


def test_tool_context():
    """Test tool context creation."""
    ctx = ToolContext(agent_name="test-agent", session_id="123")
    assert ctx.agent_name == "test-agent"
    assert ctx.session_id == "123"


def test_tool_context_metadata():
    """Test tool context metadata operations."""
    ctx = ToolContext(agent_name="test", metadata={"key": "value"})
    assert ctx.get("key") == "value"
    assert ctx.get("missing", "default") == "default"

    ctx.set("new_key", "new_value")
    assert ctx.get("new_key") == "new_value"
