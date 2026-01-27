"""Example of using the AskUserQuestion tool.

This example demonstrates how to use AskUserQuestionTool to interact with
users and get clarification during agent execution.
"""

import asyncio

from minicode.session.message import ToolContext
from minicode.tools.builtin import AskUserQuestionTool


async def example_basic_question():
    """Example 1: Basic question with callback."""
    print("=" * 60)
    print("Example 1: Basic Question with Callback")
    print("=" * 60)

    # Simulate user providing answer via callback
    async def user_callback(question: str) -> str:
        print(f"\n🤔 Agent asks: {question}")
        # In real scenario, this would get input from UI/CLI
        answer = "Python 3.10"
        print(f"✅ User answers: {answer}")
        return answer

    context = ToolContext(agent_name="demo", session_id="demo-session")
    tool = AskUserQuestionTool(question_callback=user_callback)

    result = await tool.execute(
        {"question": "Which Python version should I use?"},
        context,
    )

    print(f"\n📊 Result:")
    print(f"   Success: {result['success']}")
    print(f"   Question: {result['question']}")
    print(f"   Answer: {result['answer']}")
    print()


async def example_multi_round_conversation():
    """Example 2: Multi-round conversation."""
    print("=" * 60)
    print("Example 2: Multi-Round Conversation")
    print("=" * 60)

    # Predefined answers for demonstration
    conversation = [
        ("What is the project name?", "MyApp"),
        ("Should I use TypeScript or JavaScript?", "TypeScript"),
        ("Do you want ESLint configured?", "Yes"),
    ]

    answers_iter = iter([a for _, a in conversation])

    async def conversation_callback(question: str) -> str:
        answer = next(answers_iter)
        print(f"\n🤔 Agent: {question}")
        print(f"✅ User: {answer}")
        return answer

    context = ToolContext(agent_name="demo", session_id="demo-session")
    tool = AskUserQuestionTool(question_callback=conversation_callback)

    print("\n📝 Simulating project setup conversation:")

    for question, expected_answer in conversation:
        result = await tool.execute({"question": question}, context)
        assert result["success"] is True
        assert result["answer"] == expected_answer

    print("\n✅ Conversation completed successfully!")
    print()


async def example_with_timeout_and_default():
    """Example 3: Question with timeout and default answer."""
    print("=" * 60)
    print("Example 3: Timeout with Default Answer")
    print("=" * 60)

    # Simulate slow user response
    async def slow_user(question: str) -> str:
        print(f"\n🤔 Agent asks: {question}")
        print("⏳ User is thinking... (will timeout)")
        await asyncio.sleep(5)  # Too slow
        return "late answer"

    context = ToolContext(agent_name="demo", session_id="demo-session")
    tool = AskUserQuestionTool(question_callback=slow_user)

    result = await tool.execute(
        {
            "question": "What should be the default timeout in seconds?",
            "timeout": 1.0,  # 1 second timeout
            "default_answer": "30",
        },
        context,
    )

    print(f"\n📊 Result:")
    print(f"   Success: {result['success']}")
    print(f"   Timed out: {result['timed_out']}")
    print(f"   Used default: {result['used_default']}")
    print(f"   Answer: {result['answer']}")
    print(f"   Message: {result.get('message', 'N/A')}")
    print()


async def example_timeout_no_default():
    """Example 4: Timeout without default (inform agent user didn't respond)."""
    print("=" * 60)
    print("Example 4: Timeout Without Default")
    print("=" * 60)

    async def slow_user(question: str) -> str:
        print(f"\n🤔 Agent asks: {question}")
        print("⏳ User is thinking... (will timeout)")
        await asyncio.sleep(5)
        return "late answer"

    context = ToolContext(agent_name="demo", session_id="demo-session")
    tool = AskUserQuestionTool(question_callback=slow_user)

    result = await tool.execute(
        {
            "question": "Should I proceed with deletion?",
            "timeout": 1.0,
        },
        context,
    )

    print(f"\n📊 Result:")
    print(f"   Success: {result['success']}")
    print(f"   Timed out: {result['timed_out']}")
    print(f"   Answer: '{result['answer']}' (empty)")
    print(f"   Message: {result['message']}")
    print(
        "\n💡 Agent should interpret empty answer + timeout as 'user didn't respond'"
    )
    print()


async def example_cli_mode():
    """Example 5: CLI mode without callback (manual demonstration)."""
    print("=" * 60)
    print("Example 5: CLI Mode (No Callback)")
    print("=" * 60)

    # Create tool without callback - will use standard input
    # Note: This is commented out because it would block in automated examples
    # Uncomment to try interactively

    # context = ToolContext(agent_name="demo", session_id="demo-session")
    # tool = AskUserQuestionTool()  # No callback

    # result = await tool.execute(
    #     {
    #         "question": "What is your favorite programming language?",
    #         "default_answer": "Python",
    #         "timeout": 10.0,
    #     },
    #     context,
    # )

    # print(f"\nYour answer: {result['answer']}")

    print(
        "\n📝 CLI mode demonstration (commented out in automated example):"
    )
    print("   When no callback is provided, the tool will:")
    print("   1. Print the question to stdout")
    print("   2. Wait for user input via stdin")
    print("   3. Support timeout and default answer")
    print("   4. Run input() in thread pool to avoid blocking event loop")
    print()


async def example_choice_based_workflow():
    """Example 6: Agent workflow adapts based on user choice."""
    print("=" * 60)
    print("Example 6: Adaptive Workflow Based on User Choice")
    print("=" * 60)

    # Simulate user making a choice
    async def user_callback(question: str) -> str:
        print(f"\n🤔 Agent: {question}")
        if "database" in question.lower():
            answer = "PostgreSQL"
        elif "api" in question.lower():
            answer = "REST"
        else:
            answer = "default"
        print(f"✅ User: {answer}")
        return answer

    context = ToolContext(agent_name="demo", session_id="demo-session")
    tool = AskUserQuestionTool(question_callback=user_callback)

    # First question determines workflow
    print("\n📝 Agent adapting workflow based on user choices:")

    db_result = await tool.execute(
        {"question": "Which database do you prefer: PostgreSQL or MySQL?"},
        context,
    )

    if "postgres" in db_result["answer"].lower():
        print("   → Agent will configure PostgreSQL connection")
        api_result = await tool.execute(
            {"question": "Which API style: REST or GraphQL?"},
            context,
        )
        print(f"   → Agent will create {api_result['answer']} API")
    else:
        print("   → Agent would configure MySQL (not reached in this example)")

    print("\n✅ Workflow completed based on user preferences!")
    print()


async def example_error_handling():
    """Example 7: Handle various error scenarios."""
    print("=" * 60)
    print("Example 7: Error Handling")
    print("=" * 60)

    context = ToolContext(agent_name="demo", session_id="demo-session")

    # Error 1: Missing question
    print("\n❌ Test 1: Missing question parameter")
    tool = AskUserQuestionTool()
    result = await tool.execute({}, context)
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    # Error 2: Callback raises exception
    print("\n❌ Test 2: Callback raises exception")

    async def broken_callback(question: str) -> str:
        raise ValueError("Simulated error")

    tool = AskUserQuestionTool(question_callback=broken_callback)
    result = await tool.execute({"question": "Will this work?"}, context)
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    print()


async def main():
    """Run all examples."""
    await example_basic_question()
    await example_multi_round_conversation()
    await example_with_timeout_and_default()
    await example_timeout_no_default()
    await example_cli_mode()
    await example_choice_based_workflow()
    await example_error_handling()


if __name__ == "__main__":
    asyncio.run(main())
