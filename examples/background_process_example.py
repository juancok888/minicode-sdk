"""Example of using background process management tools.

This example demonstrates how to use BashTool, BashOutputTool, and KillShellTool
to manage long-running background processes.
"""

import asyncio

from minicode.session.message import ToolContext
from minicode.tools.builtin import BashOutputTool, BashTool, KillShellTool


async def example_simple_background():
    """Example 1: Start and monitor a simple background process."""
    print("=" * 60)
    print("Example 1: Simple Background Process")
    print("=" * 60)

    context = ToolContext(agent_name="demo", session_id="demo-session")
    bash_tool = BashTool()
    output_tool = BashOutputTool()
    kill_tool = KillShellTool()

    # Start background process
    print("\n🚀 Starting background process...")
    result = await bash_tool.execute(
        {
            "command": "for i in 1 2 3 4 5; do echo 'Count: '$i; sleep 1; done",
            "run_in_background": True,
        },
        context,
    )

    if result["success"]:
        bash_id = result["bash_id"]
        print(f"   Process started with ID: {bash_id}")

        # Monitor output multiple times
        for _ in range(3):
            await asyncio.sleep(1.5)
            output = await output_tool.execute({"bash_id": bash_id}, context)
            if output["success"]:
                print(f"\n📊 New output:")
                print(f"   {output['output']}")
                print(f"   Running: {output['is_running']}")

        # Clean up
        kill_result = await kill_tool.execute({"shell_id": bash_id}, context)
        print(f"\n🛑 Kill result: {kill_result['message']}")
    else:
        print(f"   Failed: {result.get('error')}")

    print()


async def example_filtered_output():
    """Example 2: Filter background process output with regex."""
    print("=" * 60)
    print("Example 2: Filtered Output Monitoring")
    print("=" * 60)

    context = ToolContext(agent_name="demo", session_id="demo-session")
    bash_tool = BashTool()
    output_tool = BashOutputTool()
    kill_tool = KillShellTool()

    # Start background process with mixed output
    print("\n🚀 Starting process with mixed output...")
    result = await bash_tool.execute(
        {
            "command": """
echo 'INFO: Starting process'
sleep 0.5
echo 'ERROR: Something went wrong'
sleep 0.5
echo 'INFO: Continuing...'
sleep 0.5
echo 'WARNING: Low memory'
sleep 0.5
echo 'INFO: Done'
            """,
            "run_in_background": True,
        },
        context,
    )

    if result["success"]:
        bash_id = result["bash_id"]
        print(f"   Process started with ID: {bash_id}")

        # Wait for some output
        await asyncio.sleep(2)

        # Get all output
        print("\n📊 All output:")
        all_output = await output_tool.execute({"bash_id": bash_id}, context)
        if all_output["success"]:
            print(f"   {all_output['output']}")

        # Get only errors and warnings (using new process for next read)
        await asyncio.sleep(1)
        filtered = await output_tool.execute(
            {
                "bash_id": bash_id,
                "filter": "ERROR|WARNING",
            },
            context,
        )

        print("\n⚠️  Filtered output (ERROR|WARNING only):")
        if filtered["success"]:
            if filtered["output"]:
                print(f"   {filtered['output']}")
            else:
                print("   (No new errors/warnings)")

        # Clean up
        await kill_tool.execute({"shell_id": bash_id}, context)
    else:
        print(f"   Failed: {result.get('error')}")

    print()


async def example_long_running_task():
    """Example 3: Manage a long-running task."""
    print("=" * 60)
    print("Example 3: Long-Running Task Management")
    print("=" * 60)

    context = ToolContext(agent_name="demo", session_id="demo-session")
    bash_tool = BashTool()
    output_tool = BashOutputTool()
    kill_tool = KillShellTool()

    # Simulate a long-running build/test process
    print("\n🚀 Starting long-running task (simulated build)...")
    result = await bash_tool.execute(
        {
            "command": """
echo '[1/5] Initializing...'
sleep 0.5
echo '[2/5] Compiling sources...'
sleep 0.5
echo '[3/5] Running tests...'
sleep 0.5
echo '[4/5] Packaging...'
sleep 0.5
echo '[5/5] Complete!'
            """,
            "run_in_background": True,
            "description": "Build and test project",
        },
        context,
    )

    if result["success"]:
        bash_id = result["bash_id"]
        print(f"   Process started: {bash_id}")

        # Poll for completion
        print("\n📊 Monitoring progress:")
        while True:
            await asyncio.sleep(0.7)
            output = await output_tool.execute({"bash_id": bash_id}, context)

            if output["success"]:
                if output["output"]:
                    print(f"   {output['output'].strip()}")

                if not output["is_running"]:
                    print(f"\n✅ Process finished (exit code: {output['exit_code']})")
                    break
            else:
                print(f"   Error: {output.get('error')}")
                break

        # No need to kill - already finished
    else:
        print(f"   Failed: {result.get('error')}")

    print()


async def example_kill_running_process():
    """Example 4: Kill a running process."""
    print("=" * 60)
    print("Example 4: Kill Running Process")
    print("=" * 60)

    context = ToolContext(agent_name="demo", session_id="demo-session")
    bash_tool = BashTool()
    output_tool = BashOutputTool()
    kill_tool = KillShellTool()

    # Start a process that runs indefinitely
    print("\n🚀 Starting infinite loop process...")
    result = await bash_tool.execute(
        {
            "command": "while true; do echo 'Running...'; sleep 1; done",
            "run_in_background": True,
        },
        context,
    )

    if result["success"]:
        bash_id = result["bash_id"]
        print(f"   Process started: {bash_id}")

        # Let it run for a bit
        print("\n⏱️  Letting it run for 2 seconds...")
        await asyncio.sleep(2)

        # Check output
        output = await output_tool.execute({"bash_id": bash_id}, context)
        if output["success"]:
            print(f"\n📊 Output before kill:")
            print(f"   {output['output']}")
            print(f"   Is running: {output['is_running']}")

        # Kill the process
        print("\n🛑 Killing process...")
        kill_result = await kill_tool.execute({"shell_id": bash_id}, context)

        if kill_result["success"]:
            print(f"   {kill_result['message']}")
            print(f"   Status: {kill_result['status']}")
        else:
            print(f"   Failed to kill: {kill_result.get('error')}")
    else:
        print(f"   Failed: {result.get('error')}")

    print()


async def example_multiple_processes():
    """Example 5: Manage multiple background processes."""
    print("=" * 60)
    print("Example 5: Multiple Background Processes")
    print("=" * 60)

    context = ToolContext(agent_name="demo", session_id="demo-session")
    bash_tool = BashTool()
    output_tool = BashOutputTool()
    kill_tool = KillShellTool()

    # Start multiple processes
    print("\n🚀 Starting multiple processes...")
    processes = []

    for i in range(3):
        result = await bash_tool.execute(
            {
                "command": f"echo 'Process {i+1} started'; sleep 1; echo 'Process {i+1} done'",
                "run_in_background": True,
            },
            context,
        )
        if result["success"]:
            processes.append(result["bash_id"])
            print(f"   Process {i+1} started: {result['bash_id']}")

    # Wait a bit
    await asyncio.sleep(1.5)

    # Check output from all processes
    print("\n📊 Checking output from all processes:")
    for i, bash_id in enumerate(processes):
        output = await output_tool.execute({"bash_id": bash_id}, context)
        if output["success"]:
            print(f"\n   Process {i+1}:")
            print(f"   Output: {output['output'].strip()}")
            print(f"   Running: {output['is_running']}")

    # Clean up all processes
    print("\n🧹 Cleaning up...")
    for bash_id in processes:
        await kill_tool.execute({"shell_id": bash_id}, context)

    print()


async def main():
    """Run all examples."""
    await example_simple_background()
    await example_filtered_output()
    await example_long_running_task()
    await example_kill_running_process()
    await example_multiple_processes()


if __name__ == "__main__":
    asyncio.run(main())
