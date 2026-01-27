"""Tests for AskUserQuestion tool."""

import asyncio

import pytest

from minicode.session.message import ToolContext
from minicode.tools.builtin import AskUserQuestionTool


@pytest.fixture
def tool_context():
    """Create a tool context for testing."""
    return ToolContext(agent_name="test", session_id="test-session")


# Basic functionality tests


@pytest.mark.asyncio
async def test_ask_with_callback(tool_context):
    """Test asking a question with a callback function."""

    async def mock_callback(question: str) -> str:
        return "callback answer"

    tool = AskUserQuestionTool(question_callback=mock_callback)

    result = await tool.execute(
        {"question": "What is your name?"},
        tool_context,
    )

    assert result["success"] is True
    assert result["question"] == "What is your name?"
    assert result["answer"] == "callback answer"
    assert result["timed_out"] is False
    assert result["used_default"] is False


@pytest.mark.asyncio
async def test_ask_with_sync_callback(tool_context):
    """Test asking with a synchronous callback (should still work)."""

    def sync_callback(question: str) -> str:
        return "sync answer"

    tool = AskUserQuestionTool(question_callback=sync_callback)

    result = await tool.execute(
        {"question": "Choose option A or B?"},
        tool_context,
    )

    assert result["success"] is True
    assert result["answer"] == "sync answer"
    assert result["timed_out"] is False


@pytest.mark.asyncio
async def test_ask_with_timeout_no_default(tool_context):
    """Test timeout without default answer."""

    async def slow_callback(question: str) -> str:
        await asyncio.sleep(5)  # Takes too long
        return "late answer"

    tool = AskUserQuestionTool(question_callback=slow_callback)

    result = await tool.execute(
        {
            "question": "Quick question?",
            "timeout": 0.1,  # Very short timeout
        },
        tool_context,
    )

    assert result["success"] is True
    assert result["timed_out"] is True
    assert result["used_default"] is False
    assert result["answer"] == ""
    assert "did not respond" in result["message"].lower()


@pytest.mark.asyncio
async def test_ask_with_timeout_and_default(tool_context):
    """Test timeout with default answer."""

    async def slow_callback(question: str) -> str:
        await asyncio.sleep(5)
        return "late answer"

    tool = AskUserQuestionTool(question_callback=slow_callback)

    result = await tool.execute(
        {
            "question": "Which option?",
            "timeout": 0.1,
            "default_answer": "default option",
        },
        tool_context,
    )

    assert result["success"] is True
    assert result["timed_out"] is True
    assert result["used_default"] is True
    assert result["answer"] == "default option"
    assert "default answer" in result["message"].lower()


@pytest.mark.asyncio
async def test_ask_no_timeout(tool_context):
    """Test asking without timeout (should wait indefinitely)."""

    async def callback(question: str) -> str:
        await asyncio.sleep(0.1)  # Short delay
        return "patient answer"

    tool = AskUserQuestionTool(question_callback=callback, default_timeout=None)

    result = await tool.execute(
        {"question": "Take your time?"},
        tool_context,
    )

    assert result["success"] is True
    assert result["answer"] == "patient answer"
    assert result["timed_out"] is False


@pytest.mark.asyncio
async def test_ask_missing_question(tool_context):
    """Test error when question is missing."""
    tool = AskUserQuestionTool()

    result = await tool.execute({}, tool_context)

    assert result["success"] is False
    assert "required" in result["error"].lower()


@pytest.mark.asyncio
async def test_multi_round_conversation(tool_context):
    """Test multiple rounds of questions (simulating conversation)."""
    answers = ["answer1", "answer2", "answer3"]
    call_count = [0]

    async def conversation_callback(question: str) -> str:
        answer = answers[call_count[0]]
        call_count[0] += 1
        return answer

    tool = AskUserQuestionTool(question_callback=conversation_callback)

    # Round 1
    result1 = await tool.execute(
        {"question": "First question?"},
        tool_context,
    )
    assert result1["success"] is True
    assert result1["answer"] == "answer1"

    # Round 2
    result2 = await tool.execute(
        {"question": "Second question?"},
        tool_context,
    )
    assert result2["success"] is True
    assert result2["answer"] == "answer2"

    # Round 3
    result3 = await tool.execute(
        {"question": "Third question?"},
        tool_context,
    )
    assert result3["success"] is True
    assert result3["answer"] == "answer3"

    assert call_count[0] == 3  # All questions asked


@pytest.mark.asyncio
async def test_default_answer_used_on_empty_response(tool_context):
    """Test that default is used when callback returns empty."""

    async def empty_callback(question: str) -> str:
        return ""  # User provides empty answer

    tool = AskUserQuestionTool(question_callback=empty_callback)

    result = await tool.execute(
        {
            "question": "Optional question?",
            "default_answer": "fallback",
        },
        tool_context,
    )

    assert result["success"] is True
    # Note: Empty answer is returned as-is, not replaced with default
    # Default only used on timeout
    assert result["answer"] == ""
    assert result["used_default"] is False


@pytest.mark.asyncio
async def test_whitespace_stripping(tool_context):
    """Test that answers have whitespace stripped."""

    async def whitespace_callback(question: str) -> str:
        return "  answer with spaces  "

    tool = AskUserQuestionTool(question_callback=whitespace_callback)

    result = await tool.execute(
        {"question": "Any question?"},
        tool_context,
    )

    assert result["success"] is True
    assert result["answer"] == "answer with spaces"


@pytest.mark.asyncio
async def test_callback_exception_handling(tool_context):
    """Test handling of exceptions in callback."""

    async def broken_callback(question: str) -> str:
        raise ValueError("Callback error")

    tool = AskUserQuestionTool(question_callback=broken_callback)

    result = await tool.execute(
        {"question": "Will this work?"},
        tool_context,
    )

    assert result["success"] is False
    assert "error" in result
    assert "Callback error" in result["error"]


@pytest.mark.asyncio
async def test_custom_default_timeout(tool_context):
    """Test using custom default timeout."""

    async def slow_callback(question: str) -> str:
        await asyncio.sleep(1)
        return "slow answer"

    # Tool with default timeout of 0.1s
    tool = AskUserQuestionTool(
        question_callback=slow_callback, default_timeout=0.1
    )

    # Should timeout using default
    result = await tool.execute(
        {"question": "Quick?"},
        tool_context,
    )

    assert result["success"] is True
    assert result["timed_out"] is True


@pytest.mark.asyncio
async def test_override_default_timeout(tool_context):
    """Test overriding default timeout in execute."""

    async def callback(question: str) -> str:
        await asyncio.sleep(0.2)
        return "answer"

    # Tool with default timeout of 0.1s
    tool = AskUserQuestionTool(
        question_callback=callback, default_timeout=0.1
    )

    # Override with longer timeout
    result = await tool.execute(
        {
            "question": "Question?",
            "timeout": 1.0,  # Override to longer timeout
        },
        tool_context,
    )

    assert result["success"] is True
    assert result["answer"] == "answer"
    assert result["timed_out"] is False


# Tool properties tests


def test_askuserquestion_tool_properties():
    """Test AskUserQuestionTool properties."""
    tool = AskUserQuestionTool()

    assert tool.name == "ask_user_question"
    assert len(tool.description) > 0
    assert "question" in tool.parameters_schema["properties"]
    assert "default_answer" in tool.parameters_schema["properties"]
    assert "timeout" in tool.parameters_schema["properties"]
    assert tool.parameters_schema["required"] == ["question"]


# Edge cases


@pytest.mark.asyncio
async def test_none_answer_from_callback(tool_context):
    """Test handling None return from callback."""

    async def none_callback(question: str):
        return None

    tool = AskUserQuestionTool(question_callback=none_callback)

    result = await tool.execute(
        {"question": "Question?"},
        tool_context,
    )

    assert result["success"] is True
    assert result["answer"] == ""  # None should become empty string


@pytest.mark.asyncio
async def test_very_long_question(tool_context):
    """Test with a very long question."""

    async def callback(question: str) -> str:
        return f"Answering: {question[:20]}..."

    tool = AskUserQuestionTool(question_callback=callback)

    long_question = "A" * 1000

    result = await tool.execute(
        {"question": long_question},
        tool_context,
    )

    assert result["success"] is True
    assert result["question"] == long_question
    assert "Answering:" in result["answer"]


@pytest.mark.asyncio
async def test_special_characters_in_question(tool_context):
    """Test with special characters in question."""

    async def callback(question: str) -> str:
        return "yes"

    tool = AskUserQuestionTool(question_callback=callback)

    result = await tool.execute(
        {"question": "Should I use 'quotes' & <tags>?"},
        tool_context,
    )

    assert result["success"] is True
    assert result["question"] == "Should I use 'quotes' & <tags>?"
