"""Example demonstrating the ThinkTool usage.

This example shows:
1. How to use ThinkTool to record reasoning process
2. Different types of thinking (analysis, planning, reflection, etc.)
3. How to query and manage think records with ThinkManager
"""

import asyncio

from minicode.session.message import ToolContext
from minicode.tools.builtin.think import ThinkTool, ThinkManager


async def main():
    """Demonstrate ThinkTool usage."""
    print("=" * 70)
    print("ThinkTool Example - Recording Agent Reasoning Process")
    print("=" * 70)
    print()

    # Create think tool and context
    think_tool = ThinkTool()
    context = ToolContext(agent_name="example_agent")

    # Example 1: Analysis thinking
    print("1. Analysis Thinking:")
    print("-" * 70)
    result = await think_tool.execute(
        {
            "type": "analysis",
            "content": """Looking at the bug report:
- Error occurs in the data processing pipeline
- Happens only with datasets > 10MB
- Stack trace points to memory allocation

Hypothesis: The issue is likely related to loading entire dataset into memory.
The code should use streaming/chunked processing instead.""",
            "title": "Bug Analysis: Memory Error in Large Datasets",
            "tags": ["bug", "performance", "memory"],
        },
        context,
    )
    print(result["output"])
    print(f"\n✓ Recorded with ID: {result['think_id']}\n")

    # Example 2: Planning thinking
    print("2. Planning Thinking:")
    print("-" * 70)
    result = await think_tool.execute(
        {
            "type": "planning",
            "content": """Implementation plan for streaming data processor:

1. **Refactor data loader**
   - Replace pd.read_csv() with chunked reading
   - Use chunk_size parameter (e.g., 1000 rows)

2. **Update processing logic**
   - Modify transform() to work on chunks
   - Accumulate results incrementally

3. **Add progress reporting**
   - Track processed rows
   - Display progress bar

4. **Write tests**
   - Test with small chunks (fast)
   - Test with large file (integration test)

5. **Update documentation**
   - Explain chunked processing
   - Add performance benchmarks""",
            "title": "Fix Implementation Plan",
            "tags": ["planning", "refactoring"],
        },
        context,
    )
    print(result["output"])
    print(f"\n✓ Recorded with ID: {result['think_id']}\n")

    # Example 3: Observation
    print("3. Observation During Implementation:")
    print("-" * 70)
    result = await think_tool.execute(
        {
            "type": "observation",
            "content": "The existing code already has a 'batch_size' parameter, but it's not being used! "
            "This will make the fix much simpler - just need to activate that code path.",
            "tags": ["implementation"],
        },
        context,
    )
    print(result["output"])
    print(f"\n✓ Recorded with ID: {result['think_id']}\n")

    # Example 4: Reasoning
    print("4. Reasoning Through Edge Cases:")
    print("-" * 70)
    result = await think_tool.execute(
        {
            "type": "reasoning",
            "content": """Edge case analysis:

If chunk_size = 1000 and file has 2500 rows:
- Chunk 1: rows 0-999 (1000 rows) ✓
- Chunk 2: rows 1000-1999 (1000 rows) ✓
- Chunk 3: rows 2000-2499 (500 rows) ✓

The last chunk has fewer rows, so any processing logic must handle variable chunk sizes.
Current code assumes fixed-size chunks → needs adjustment.""",
            "title": "Edge Case: Variable Chunk Sizes",
            "tags": ["edge-cases"],
        },
        context,
    )
    print(result["output"])
    print(f"\n✓ Recorded with ID: {result['think_id']}\n")

    # Example 5: Reflection after testing
    print("5. Reflection After Testing:")
    print("-" * 70)
    result = await think_tool.execute(
        {
            "type": "reflection",
            "content": """First implementation attempt failed because:
- I forgot to reset the accumulator between chunks
- This caused duplicate results

Lesson learned: When refactoring to chunked processing, pay careful attention to stateful variables.
Always reset state between chunks unless explicitly accumulating.

Second attempt: Added accumulator.clear() at start of each chunk → tests pass!""",
            "title": "Implementation Reflection",
            "tags": ["lesson-learned", "debugging"],
        },
        context,
    )
    print(result["output"])
    print(f"\n✓ Recorded with ID: {result['think_id']}\n")

    # Query think records
    print("\n" + "=" * 70)
    print("ThinkManager: Querying Think Records")
    print("=" * 70)
    print()

    # Get all thinks
    print("📊 All Think Records:")
    print("-" * 70)
    all_thinks = ThinkManager.get_all_thinks(context)
    print(f"Total: {len(all_thinks)} records\n")

    # Filter by type
    print("📋 Planning Thinks:")
    planning = ThinkManager.get_thinks_by_type(context, "planning")
    for think in planning:
        print(f"  - [{think['id']}] {think.get('title', 'Untitled')}")
    print()

    print("💭 Reflection Thinks:")
    reflection = ThinkManager.get_thinks_by_type(context, "reflection")
    for think in reflection:
        print(f"  - [{think['id']}] {think.get('title', 'Untitled')}")
    print()

    # Filter by tags
    print("🏷️  Thinks Tagged 'bug':")
    bug_thinks = ThinkManager.get_thinks_by_tags(context, ["bug"])
    for think in bug_thinks:
        print(f"  - [{think['id']}] {think['type']}: {think.get('title', 'Untitled')}")
    print()

    print("🏷️  Thinks Tagged 'lesson-learned':")
    lesson_thinks = ThinkManager.get_thinks_by_tags(context, ["lesson-learned"])
    for think in lesson_thinks:
        print(f"  - [{think['id']}] {think['type']}: {think.get('title', 'Untitled')}")
    print()

    # Get formatted summary
    print("\n" + "=" * 70)
    print("Summary Report")
    print("=" * 70)
    print()
    summary = ThinkManager.format_think_summary(context)
    print(summary)

    # Example: Retrieve specific think by ID
    print("\n" + "=" * 70)
    print("Retrieve Specific Think Record")
    print("=" * 70)
    print()
    if all_thinks:
        first_id = all_thinks[0]["id"]
        think = ThinkManager.get_think_by_id(context, first_id)
        if think:
            print(f"ID: {think['id']}")
            print(f"Type: {think['type']}")
            print(f"Title: {think.get('title', 'N/A')}")
            print(f"Tags: {', '.join(think.get('tags', []))}")
            print(f"Timestamp: {think['timestamp']}")
            print(f"\nContent:\n{think['content']}")


if __name__ == "__main__":
    asyncio.run(main())
