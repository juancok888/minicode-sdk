"""Example demonstrating the SkillTool usage.

This example shows:
1. How to create skills in .minicode/skills directories
2. How to use SkillTool to load and execute skills
3. How skills are discovered from multiple paths
"""

import asyncio
import os
import tempfile
from pathlib import Path

from minicode.session.message import ToolContext
from minicode.skills.loader import SkillLoader
from minicode.tools.builtin.skill import SkillTool


async def main():
    """Demonstrate SkillTool usage."""
    # Create a temporary skills directory
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / ".minicode" / "skills"
        skills_dir.mkdir(parents=True)

        # Create a sample skill: data-analysis
        data_analysis_dir = skills_dir / "data-analysis"
        data_analysis_dir.mkdir()
        (data_analysis_dir / "SKILL.md").write_text(
            """---
name: data-analysis
description: Analyze datasets and generate insights
---

# Data Analysis Skill

This skill helps you analyze datasets and generate meaningful insights.

## Steps

1. **Load the data**
   - Use pandas to load CSV, Excel, or JSON files
   - Check for missing values and data types

2. **Clean the data**
   - Handle missing values (drop, fill, interpolate)
   - Remove duplicates
   - Fix data types

3. **Explore the data**
   - Generate summary statistics
   - Create visualizations (histograms, scatter plots, etc.)
   - Identify correlations

4. **Generate insights**
   - Document key findings
   - Create actionable recommendations

## Example Code

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load data
df = pd.read_csv('data.csv')

# Summary statistics
print(df.describe())

# Visualize
df.hist(figsize=(10, 8))
plt.tight_layout()
plt.savefig('analysis.png')
```
"""
        )

        # Create another skill: code-review
        code_review_dir = skills_dir / "code-review"
        code_review_dir.mkdir()
        (code_review_dir / "SKILL.md").write_text(
            """---
name: code-review
description: Review code for best practices and issues
---

# Code Review Skill

This skill guides you through reviewing code for quality and best practices.

## Review Checklist

### Code Quality
- [ ] Clear and descriptive variable names
- [ ] Functions are small and focused
- [ ] No code duplication
- [ ] Proper error handling

### Testing
- [ ] Unit tests cover key functionality
- [ ] Edge cases are tested
- [ ] Test names are descriptive

### Documentation
- [ ] Functions have docstrings
- [ ] Complex logic is commented
- [ ] README is up to date

### Performance
- [ ] No obvious performance bottlenecks
- [ ] Database queries are optimized
- [ ] Caching is used where appropriate

### Security
- [ ] Input validation is present
- [ ] No hardcoded secrets
- [ ] SQL injection prevention
- [ ] XSS prevention (for web apps)
"""
        )

        # Initialize SkillTool with the custom skills directory
        skill_loader = SkillLoader(skill_dirs=[str(skills_dir)])
        skill_tool = SkillTool(skill_loader=skill_loader)

        print("=" * 70)
        print("Skill Tool Example")
        print("=" * 70)
        print()

        # 1. Show the tool description (lists available skills)
        print("1. Tool Description (listing available skills):")
        print("-" * 70)
        description = skill_tool.description
        # Print first few lines to show the format
        lines = description.split("\n")
        for line in lines[:30]:
            print(line)
        print("...")
        print()

        # 2. Show the parameters schema
        print("2. Parameters Schema:")
        print("-" * 70)
        print(skill_tool.parameters_schema)
        print()

        # 3. Execute the data-analysis skill
        print("3. Executing 'data-analysis' skill:")
        print("-" * 70)
        context = ToolContext(agent_name="example_agent")
        result = await skill_tool.execute({"skill": "data-analysis"}, context)

        print(f"Success: {result['success']}")
        print(f"Skill Name: {result['skill_name']}")
        print(f"Skill Dir: {result['skill_dir']}")
        print()
        print("Content:")
        print(result["data"])
        print()

        # 4. Execute the code-review skill
        print("4. Executing 'code-review' skill:")
        print("-" * 70)
        result = await skill_tool.execute({"skill": "code-review"}, context)

        print(f"Success: {result['success']}")
        print(f"Skill Name: {result['skill_name']}")
        print()
        print("Content (first 500 chars):")
        print(result["data"][:500] + "...")
        print()

        # 5. Try to execute a non-existent skill
        print("5. Executing non-existent skill (should fail):")
        print("-" * 70)
        try:
            await skill_tool.execute({"skill": "nonexistent"}, context)
        except ValueError as e:
            print(f"Error (expected): {e}")
        print()

        # 6. Show environment variable support
        print("6. Environment Variable Support:")
        print("-" * 70)
        print("You can set MINICODE_SKILLS_DIR to add additional skill directories:")
        print(f"  export MINICODE_SKILLS_DIR=/path/to/custom/skills")
        print()
        print("Default search paths:")
        print("  - .minicode/skills")
        print("  - ~/.minicode/skills")
        print("  - $MINICODE_SKILLS_DIR (if set)")
        print()


if __name__ == "__main__":
    asyncio.run(main())
