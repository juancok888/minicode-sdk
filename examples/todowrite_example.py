"""Example of using the TodoWrite tool for task management.

This example demonstrates how to use the TodoWriteTool to track and manage
tasks during an agent's workflow.
"""

import asyncio

from minicode.session.message import ToolContext
from minicode.tools.builtin import TodoWriteTool


async def example_basic_todo_list():
    """Example 1: Create a basic todo list."""
    print("=" * 60)
    print("Example 1: Basic Todo List")
    print("=" * 60)

    tool = TodoWriteTool()
    context = ToolContext(agent_name="demo", session_id="demo-session")
    context.metadata = {}

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Implement authentication system",
                    "activeForm": "Implementing authentication system",
                    "status": "pending",
                },
                {
                    "content": "Write unit tests",
                    "activeForm": "Writing unit tests",
                    "status": "in_progress",
                },
                {
                    "content": "Setup project structure",
                    "activeForm": "Setting up project structure",
                    "status": "completed",
                },
            ]
        },
        context,
    )

    print(f"Success: {result['success']}")
    print(f"Total tasks: {result['total_tasks']}")
    print(f"Status counts: {result['status_counts']}")
    if "warning" in result:
        print(f"Warning: {result['warning']}")
    print()


async def example_task_progression():
    """Example 2: Demonstrate task progression over time."""
    print("=" * 60)
    print("Example 2: Task Progression")
    print("=" * 60)

    tool = TodoWriteTool()
    context = ToolContext(agent_name="demo", session_id="demo-session")
    context.metadata = {}

    # Initial state: all pending
    print("\n📋 Initial state:")
    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Research API design",
                    "activeForm": "Researching API design",
                    "status": "pending",
                },
                {
                    "content": "Implement endpoints",
                    "activeForm": "Implementing endpoints",
                    "status": "pending",
                },
                {
                    "content": "Add error handling",
                    "activeForm": "Adding error handling",
                    "status": "pending",
                },
            ]
        },
        context,
    )
    print(f"   Status: {result['status_counts']}")

    # Start first task
    print("\n🚀 Starting first task:")
    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Research API design",
                    "activeForm": "Researching API design",
                    "status": "in_progress",
                },
                {
                    "content": "Implement endpoints",
                    "activeForm": "Implementing endpoints",
                    "status": "pending",
                },
                {
                    "content": "Add error handling",
                    "activeForm": "Adding error handling",
                    "status": "pending",
                },
            ]
        },
        context,
    )
    print(f"   Status: {result['status_counts']}")

    # Complete first, start second
    print("\n✅ Complete first task, start second:")
    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Research API design",
                    "activeForm": "Researching API design",
                    "status": "completed",
                },
                {
                    "content": "Implement endpoints",
                    "activeForm": "Implementing endpoints",
                    "status": "in_progress",
                },
                {
                    "content": "Add error handling",
                    "activeForm": "Adding error handling",
                    "status": "pending",
                },
            ]
        },
        context,
    )
    print(f"   Status: {result['status_counts']}")

    # Complete all
    print("\n🎉 All tasks completed:")
    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Research API design",
                    "activeForm": "Researching API design",
                    "status": "completed",
                },
                {
                    "content": "Implement endpoints",
                    "activeForm": "Implementing endpoints",
                    "status": "completed",
                },
                {
                    "content": "Add error handling",
                    "activeForm": "Adding error handling",
                    "status": "completed",
                },
            ]
        },
        context,
    )
    print(f"   Status: {result['status_counts']}")
    print()


async def example_warning_multiple_in_progress():
    """Example 3: Warning when multiple tasks are in_progress."""
    print("=" * 60)
    print("Example 3: Warning - Multiple Tasks In Progress")
    print("=" * 60)

    tool = TodoWriteTool()
    context = ToolContext(agent_name="demo", session_id="demo-session")
    context.metadata = {}

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Task 1",
                    "activeForm": "Doing task 1",
                    "status": "in_progress",
                },
                {
                    "content": "Task 2",
                    "activeForm": "Doing task 2",
                    "status": "in_progress",
                },
                {
                    "content": "Task 3",
                    "activeForm": "Doing task 3",
                    "status": "in_progress",
                },
            ]
        },
        context,
    )

    print(f"Success: {result['success']}")
    print(f"Status counts: {result['status_counts']}")
    if "warning" in result:
        print(f"⚠️  {result['warning']}")
    print()


async def example_warning_no_in_progress():
    """Example 4: Warning when no task is in_progress but pending exist."""
    print("=" * 60)
    print("Example 4: Warning - No Task In Progress")
    print("=" * 60)

    tool = TodoWriteTool()
    context = ToolContext(agent_name="demo", session_id="demo-session")
    context.metadata = {}

    result = await tool.execute(
        {
            "todos": [
                {
                    "content": "Task 1",
                    "activeForm": "Doing task 1",
                    "status": "pending",
                },
                {
                    "content": "Task 2",
                    "activeForm": "Doing task 2",
                    "status": "pending",
                },
            ]
        },
        context,
    )

    print(f"Success: {result['success']}")
    print(f"Status counts: {result['status_counts']}")
    if "warning" in result:
        print(f"⚠️  {result['warning']}")
    print()


async def example_complex_workflow():
    """Example 5: Complex multi-step workflow."""
    print("=" * 60)
    print("Example 5: Complex Multi-Step Workflow")
    print("=" * 60)

    tool = TodoWriteTool()
    context = ToolContext(agent_name="demo", session_id="demo-session")
    context.metadata = {}

    # Bug fix workflow
    todos = [
        {
            "content": "Reproduce bug",
            "activeForm": "Reproducing bug",
            "status": "completed",
        },
        {
            "content": "Identify root cause",
            "activeForm": "Identifying root cause",
            "status": "completed",
        },
        {
            "content": "Implement fix",
            "activeForm": "Implementing fix",
            "status": "in_progress",
        },
        {
            "content": "Write regression test",
            "activeForm": "Writing regression test",
            "status": "pending",
        },
        {
            "content": "Update documentation",
            "activeForm": "Updating documentation",
            "status": "pending",
        },
        {
            "content": "Code review",
            "activeForm": "In code review",
            "status": "pending",
        },
    ]

    result = await tool.execute({"todos": todos}, context)

    print(f"Workflow: Bug Fix Process")
    print(f"Total tasks: {result['total_tasks']}")
    print(f"Status counts: {result['status_counts']}")
    print()
    print("Progress:")
    completed = result["status_counts"]["completed"]
    total = result["total_tasks"]
    percentage = (completed / total * 100) if total > 0 else 0
    print(f"  ✅ Completed: {completed}/{total} ({percentage:.1f}%)")
    print(f"  🔄 In Progress: {result['status_counts']['in_progress']}")
    print(f"  ⏳ Pending: {result['status_counts']['pending']}")
    print()


async def main():
    """Run all examples."""
    await example_basic_todo_list()
    await example_task_progression()
    await example_warning_multiple_in_progress()
    await example_warning_no_in_progress()
    await example_complex_workflow()


if __name__ == "__main__":
    asyncio.run(main())
