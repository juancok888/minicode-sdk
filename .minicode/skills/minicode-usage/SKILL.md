---
name: minicode_usage
description: Guide for using the minicode-sdk library. Use this skill when the user wants to learn how to use minicode-sdk to build AI agents, integrate tools, use MCP servers, or configure the SDK.
---

# minicode-sdk Usage Guide

## Installation

```bash
pip install minicode-sdk
```

## Quick Start

### Basic Agent

```python
import asyncio
from minicode import Agent
from minicode.llm import OpenAILLM

async def main():
    agent = Agent(
        name="assistant",
        llm=OpenAILLM(api_key="your-api-key"),
    )

    response = await agent.generate("Hello, how are you?")
    print(response)

asyncio.run(main())
```

### Streaming Response

```python
async def main():
    agent = Agent(name="assistant", llm=OpenAILLM(api_key="your-key"))

    async for chunk in agent.stream("Tell me a story"):
        if chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
```

## Adding Tools

### Built-in Tools

```python
from minicode.tools.builtin import ReadTool, WriteTool, BashTool

agent = Agent(
    name="assistant",
    llm=my_llm,
    tools=[ReadTool(), WriteTool(), BashTool()],
)
```

### Custom Tools

```python
from minicode.tools.base import BaseTool

class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Description of what this tool does"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "First parameter"},
            },
            "required": ["param1"],
        }

    async def execute(self, params: dict, context) -> dict:
        # Implement tool logic
        return {"success": True, "result": "..."}
```

## MCP Integration

### Method 1: Direct Configuration

```python
async with Agent(
    name="assistant",
    llm=my_llm,
    mcp_servers=[
        {
            "name": "memory",
            "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
        }
    ],
) as agent:
    response = await agent.generate("Remember that my name is Alice")
```

### Method 2: Configuration File

Create `.minicode/mcp.json`:

```json
{
  "mcpServers": {
    "memory": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

Then use the agent (MCP servers are loaded automatically):

```python
async with Agent(name="assistant", llm=my_llm) as agent:
    # MCP tools are automatically available
    pass
```

## Agent Instructions

Create `.minicode/AGENT.md` to define custom instructions:

```markdown
# Project Guidelines

- Use Google-style docstrings
- All code must be production-ready
- Ask for clarification if requirements are unclear
```

Instructions are automatically injected into user messages.

Disable with:

```python
agent = Agent(
    name="assistant",
    llm=my_llm,
    use_agent_instructions=False,
)
```

## Skills

### Using SkillTool

```python
from minicode.tools.builtin import SkillTool

agent = Agent(
    name="assistant",
    llm=my_llm,
    tools=[SkillTool()],
)
```

### Creating Skills

Create `.minicode/skills/my-skill/SKILL.md`:

```markdown
---
name: my_skill
description: What this skill does and when to use it.
---

# Skill Content

Instructions for the agent when this skill is invoked.
```

## Configuration Locations

| Config | Project Level | User Level |
|--------|---------------|------------|
| MCP | `.minicode/mcp.json` | `~/.minicode/mcp.json` |
| Agent Instructions | `.minicode/AGENT.md` | `~/.minicode/AGENT.md` |
| Skills | `.minicode/skills/` | `~/.minicode/skills/` |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MINICODE_CONFIG` | Custom path for MCP config file |
| `MINICODE_AGENT_INSTRUCTIONS` | Custom path for agent instructions, or "false" to disable |
| `MINICODE_SKILLS_DIR` | Custom path for skills directory |
