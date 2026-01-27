"""Example: Using NotebookEdit tool to manipulate Jupyter notebooks.

This example demonstrates how to edit, insert, and delete cells in Jupyter notebooks.
"""

import asyncio
import json
from pathlib import Path

from minicode.session.message import ToolContext
from minicode.tools.builtin import NotebookEditTool


async def create_sample_notebook(path: Path):
    """Create a sample notebook for demonstration."""
    notebook = {
        "cells": [
            {
                "id": "intro-cell",
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# Data Analysis Example\n", "This notebook demonstrates data analysis."],
            },
            {
                "id": "import-cell",
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [],
                "source": ["import pandas as pd\n", "import numpy as np"],
            },
            {
                "id": "data-cell",
                "cell_type": "code",
                "execution_count": 2,
                "metadata": {},
                "outputs": [],
                "source": ["data = pd.DataFrame({\n", "    'x': [1, 2, 3, 4, 5],\n", "    'y': [2, 4, 6, 8, 10]\n", "})"],
            },
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=1)

    print(f"✓ Created sample notebook: {path}")


async def example_1_replace_cell():
    """Example 1: Replace a cell's content."""
    print("\n" + "=" * 80)
    print("Example 1: Replace Cell Content")
    print("=" * 80)

    # Create sample notebook
    nb_path = Path("/tmp/example_notebook.ipynb")
    await create_sample_notebook(nb_path)

    context = ToolContext(agent_name="example", session_id="demo")
    tool = NotebookEditTool()

    # Replace the data cell with new data
    print("\n[Action] Replacing data-cell with new DataFrame...")
    result = await tool.execute(
        {
            "notebook_path": str(nb_path),
            "cell_id": "data-cell",
            "new_source": """data = pd.DataFrame({
    'x': [1, 2, 3, 4, 5],
    'y': [2, 4, 6, 8, 10],
    'z': [3, 6, 9, 12, 15]
})
print(data.head())""",
        },
        context,
    )

    if result["success"]:
        print(f"✓ {result['message']}")
        print(f"✓ Notebook now has {result['cells_count']} cells")
    else:
        print(f"✗ Failed: {result['error']}")


async def example_2_insert_cell():
    """Example 2: Insert a new cell."""
    print("\n" + "=" * 80)
    print("Example 2: Insert New Cell")
    print("=" * 80)

    nb_path = Path("/tmp/example_notebook.ipynb")
    context = ToolContext(agent_name="example", session_id="demo")
    tool = NotebookEditTool()

    # Insert a visualization cell after the data cell
    print("\n[Action] Inserting a new visualization cell after data-cell...")
    result = await tool.execute(
        {
            "notebook_path": str(nb_path),
            "edit_mode": "insert",
            "cell_id": "data-cell",
            "cell_type": "code",
            "new_source": """import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))
plt.scatter(data['x'], data['y'])
plt.xlabel('X')
plt.ylabel('Y')
plt.title('X vs Y Scatter Plot')
plt.show()""",
        },
        context,
    )

    if result["success"]:
        print(f"✓ {result['message']}")
        print(f"✓ Notebook now has {result['cells_count']} cells")
    else:
        print(f"✗ Failed: {result['error']}")


async def example_3_change_cell_type():
    """Example 3: Change cell type from code to markdown."""
    print("\n" + "=" * 80)
    print("Example 3: Change Cell Type")
    print("=" * 80)

    nb_path = Path("/tmp/example_notebook.ipynb")
    context = ToolContext(agent_name="example", session_id="demo")
    tool = NotebookEditTool()

    # Change import cell to markdown (documenting imports)
    print("\n[Action] Converting import-cell to markdown documentation...")
    result = await tool.execute(
        {
            "notebook_path": str(nb_path),
            "cell_id": "import-cell",
            "cell_type": "markdown",
            "new_source": """## Required Libraries

This analysis uses:
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **matplotlib**: Data visualization""",
        },
        context,
    )

    if result["success"]:
        print(f"✓ {result['message']}")
    else:
        print(f"✗ Failed: {result['error']}")


async def example_4_insert_at_beginning():
    """Example 4: Insert a cell at the beginning."""
    print("\n" + "=" * 80)
    print("Example 4: Insert Cell at Beginning")
    print("=" * 80)

    nb_path = Path("/tmp/example_notebook.ipynb")
    context = ToolContext(agent_name="example", session_id="demo")
    tool = NotebookEditTool()

    # Insert a title cell at the beginning
    print("\n[Action] Inserting title cell at the beginning...")
    result = await tool.execute(
        {
            "notebook_path": str(nb_path),
            "edit_mode": "insert",
            "cell_id": None,  # None = insert at beginning
            "cell_type": "markdown",
            "new_source": """# Advanced Data Analysis Notebook

Author: Data Science Team
Date: 2026-01-17
Version: 1.0""",
        },
        context,
    )

    if result["success"]:
        print(f"✓ {result['message']}")
        print(f"✓ Notebook now has {result['cells_count']} cells")
    else:
        print(f"✗ Failed: {result['error']}")


async def example_5_delete_cell():
    """Example 5: Delete a cell."""
    print("\n" + "=" * 80)
    print("Example 5: Delete Cell")
    print("=" * 80)

    nb_path = Path("/tmp/example_notebook.ipynb")
    context = ToolContext(agent_name="example", session_id="demo")
    tool = NotebookEditTool()

    # Delete the intro cell (we have a better title now)
    print("\n[Action] Deleting old intro-cell...")
    result = await tool.execute(
        {
            "notebook_path": str(nb_path),
            "edit_mode": "delete",
            "cell_id": "intro-cell",
            "new_source": "",  # Required parameter but not used
        },
        context,
    )

    if result["success"]:
        print(f"✓ {result['message']}")
        print(f"✓ Notebook now has {result['cells_count']} cells")
    else:
        print(f"✗ Failed: {result['error']}")


async def show_final_notebook():
    """Display the final notebook structure."""
    print("\n" + "=" * 80)
    print("Final Notebook Structure")
    print("=" * 80)

    nb_path = Path("/tmp/example_notebook.ipynb")

    with open(nb_path, "r") as f:
        notebook = json.load(f)

    print(f"\n✓ Total cells: {len(notebook['cells'])}\n")

    for i, cell in enumerate(notebook["cells"], 1):
        cell_type = cell["cell_type"]
        source_preview = "".join(cell["source"])[:60].replace("\n", " ")
        print(f"{i}. [{cell_type:>8}] {source_preview}...")

    print(f"\n✓ Notebook saved at: {nb_path}")
    print("  You can open it with: jupyter notebook /tmp/example_notebook.ipynb")


async def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 18 + "NotebookEdit Tool Examples" + " " * 34 + "║")
    print("╚" + "=" * 78 + "╝")

    # Run examples
    await example_1_replace_cell()
    await example_2_insert_cell()
    await example_3_change_cell_type()
    await example_4_insert_at_beginning()
    await example_5_delete_cell()
    await show_final_notebook()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
