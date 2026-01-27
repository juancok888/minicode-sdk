# minicode

[中文文档](README_CN.md)

A Python SDK for building AI agents with LLM, tools, skills, and MCP support.

## Overview

**minicode** is a clean, extensible framework for building AI agents in Python. Minicode provides a simple yet powerful abstraction layer for:

- **LLM Integration** - Support for any LLM provider through a common interface
- **Tool System** - Extensible tool framework with JSON Schema validation
- **MCP Support** - Connect to Model Context Protocol servers for additional capabilities
- **Skills** - Load and use skills from skill directories
- **Async First** - Built with async/await for efficient I/O operations
- **Type Safe** - Full type annotations for better IDE support

## Installation

```bash
pip install minicode-sdk
```

## Quick Start

> **Tip:** The easiest way to get started is to use the built-in skills in `.minicode/skills/`. Simply ask your AI coding assistant (like Claude Code) to invoke `minicode_usage` or `minicode_contributing` skills to help you develop with minicode-sdk.

### Claude Code in 20 Lines

A production-ready coding assistant with file ops, shell execution, web access, sub-agents, and more - all in just 20 lines of code.

See the full example: [examples/claude_code_in_20_lines.py](examples/claude_code_in_20_lines.py)

```python
import asyncio, os
from minicode import Agent
from minicode.llm import OpenRouterLLM
from minicode.tools.builtin import *

async def main():
    llm = OpenRouterLLM(api_key=os.getenv("OPENROUTER_API_KEY"), model="anthropic/claude-sonnet-4")
    tools = [ReadTool(), WriteTool(), EditTool(), GlobTool(), GrepTool(), BashTool(),
             WebFetchTool(), WebSearchTool(), TaskTool(), ThinkTool(), SkillTool(), AskUserQuestionTool()]
    agent = Agent("ClaudeCode", llm, "You are a helpful coding assistant.", tools)
    while True:
        if msg := input("\n> User: ").strip():
            print(f"\n> Agent:")
            async for chunk in agent.stream(msg):
                chunk_type = chunk.get("type")
                if chunk_type == "content":
                    print(chunk.get("content", ""), end="", flush=True)
                elif chunk_type == "tool_call":
                    func = chunk.get("tool_call", {}).get("function", {})
                    print(f"\n[TOOL] {func.get('name')} | args: {func.get('arguments')}")
                elif chunk_type == "tool_result":
                    print(f"[RESULT] {chunk.get('tool_name')}: {chunk.get('result')}")
            print()

asyncio.run(main())
```

```bash
# Setup
export OPENROUTER_API_KEY=your_key
python examples/claude_code_in_20_lines.py
```

## Core Concepts

### 1. Agent

The `Agent` class is the core of minicode. It combines an LLM, tools, and session management:

```python
from minicode import Agent

agent = Agent(
    name="my-agent",
    llm=my_llm,
    tools=[tool1, tool2],
    prompt="System prompt for the agent",
    temperature=0.7,
    top_p=1.0,
    mode="primary",  # or "subagent" or "all"
)
```

**Key Methods:**
- `stream(message)` - Stream responses from the agent
- `generate(message)` - Get a complete response (non-streaming)
- `add_tool(tool)` - Add a tool to the agent
- `reset_session()` - Clear conversation history

### 2. LLM Abstraction

minicode provides a clean abstraction for LLM providers:

```python
from minicode.llm import BaseLLM

class MyCustomLLM(BaseLLM):
    async def stream(self, messages, tools=None, **kwargs):
        # Implement streaming logic
        yield {"type": "content", "content": "Hello"}
        yield {"type": "done", "finish_reason": "stop"}
    
    async def generate(self, messages, **kwargs):
        # Implement non-streaming logic
        return {"content": "Hello", "finish_reason": "stop"}
```

**Built-in Implementations:**
- `OpenAILLM` - OpenAI API integration (GPT-4, GPT-3.5, etc.)

### 3. Tool System

Tools allow agents to interact with the environment:

```python
from minicode import BaseTool, ToolContext
from typing import Dict, Any

class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "What this tool does"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Input text"}
            },
            "required": ["input"]
        }
    
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        return {
            "success": True,
            "data": f"Processed: {params['input']}"
        }
```

**Built-in Tools:**
- `AskUserQuestionTool` - Ask questions to users and wait for answers with timeout support
- `BashTool` - Execute bash commands with timeout support and background execution
- `BashOutputTool` - Monitor output from background bash processes
- `KillShellTool` - Terminate background bash processes
- `ReadTool` - Read file contents
- `WriteTool` - Write content to files
- `EditTool` - Precise string replacement in files
- `GlobTool` - File pattern matching (e.g., `**/*.py`)
- `GrepTool` - Code search with regex (ripgrep + Python fallback)
- `WebFetchTool` - Fetch web content with HTML to Markdown/text conversion
- `WebSearchTool` - Web search with configurable backends (Exa, DuckDuckGo)
- `NotebookEditTool` - Edit Jupyter notebook cells (replace/insert/delete)
- `TodoWriteTool` - Create and manage structured task lists for tracking progress
- `TaskTool` - Launch sub-agents to handle complex tasks in isolated sessions
- `TaskOutputTool` - Sub-agents use this to return results early
- `SkillTool` - Load and execute skills from skill directories
- `ThinkTool` - Record agent's reasoning and thinking process for transparency

**Web Tools Usage:**

```python
from minicode.tools.builtin import WebFetchTool, WebSearchTool

# Fetch web content
webfetch = WebFetchTool()
result = await webfetch.execute(
    {"url": "https://example.com", "format": "markdown"},
    context
)

# Search the web
websearch = WebSearchTool(default_backend="exa")
result = await websearch.execute(
    {
        "query": "Python tutorials",
        "num_results": 10,
        "type": "deep",  # Exa-specific: auto, fast, or deep
        "livecrawl": "preferred"  # Exa-specific: fallback or preferred
    },
    context
)
```

**WebFetch Features:**
- Supports multiple output formats: `text`, `markdown`, `html`
- Automatic HTML to Markdown conversion using html2text
- Plain text extraction with script/style removal
- Configurable timeout (default 30s, max 120s)
- 5MB size limit for responses

**WebSearch Features:**
- Configurable backends: `exa` (default), `duckduckgo` (requires duckduckgo-search package)
- Exa backend supports advanced options: search type (auto/fast/deep), live crawl mode
- Customizable number of results
- LLM-optimized context from Exa

**Notebook Tools Usage:**

```python
from minicode.tools.builtin import NotebookEditTool

# Replace a cell's content
notebook_tool = NotebookEditTool()
result = await notebook_tool.execute(
    {
        "notebook_path": "/path/to/notebook.ipynb",
        "cell_id": "abc123",
        "new_source": "print('Hello, World!')"
    },
    context
)

# Insert a new cell
result = await notebook_tool.execute(
    {
        "notebook_path": "/path/to/notebook.ipynb",
        "edit_mode": "insert",
        "cell_id": "abc123",  # Insert after this cell
        "cell_type": "code",
        "new_source": "x = 42"
    },
    context
)

# Delete a cell
result = await notebook_tool.execute(
    {
        "notebook_path": "/path/to/notebook.ipynb",
        "edit_mode": "delete",
        "cell_id": "abc123",
        "new_source": ""  # Required but not used
    },
    context
)
```

**NotebookEdit Features:**
- Replace cell content by cell ID
- Insert new cells (code or markdown) at any position
- Delete cells by ID
- Change cell type (code ↔ markdown)
- Automatically clears outputs when editing code cells
- Preserves notebook metadata and structure

**TodoWrite Usage:**

```python
from minicode.tools.builtin import TodoWriteTool

# Create and manage task lists
todo_tool = TodoWriteTool()
result = await todo_tool.execute(
    {
        "todos": [
            {
                "content": "Implement feature X",
                "activeForm": "Implementing feature X",
                "status": "pending"
            },
            {
                "content": "Write tests",
                "activeForm": "Writing tests",
                "status": "in_progress"
            },
            {
                "content": "Update documentation",
                "activeForm": "Updating documentation",
                "status": "completed"
            }
        ]
    },
    context
)
```

**TodoWrite Features:**
- Track multiple tasks with status (pending/in_progress/completed)
- Each task has `content` (imperative form) and `activeForm` (present continuous)
- Provides visibility into agent progress
- Warns if more than one task is in_progress
- Warns if no task is in_progress when pending tasks exist
- Helps organize complex multi-step tasks

**Background Process Tools Usage:**

```python
from minicode.tools.builtin import BashTool, BashOutputTool, KillShellTool

# Start a background process
bash_tool = BashTool()
result = await bash_tool.execute(
    {
        "command": "python long_running_script.py",
        "run_in_background": True
    },
    context
)

bash_id = result["bash_id"]

# Monitor output from background process
output_tool = BashOutputTool()
output = await output_tool.execute(
    {
        "bash_id": bash_id,
        "filter": "ERROR|WARNING"  # Optional regex filter
    },
    context
)
print(output["output"])  # Only new output since last check

# Kill background process
kill_tool = KillShellTool()
result = await kill_tool.execute(
    {"shell_id": bash_id},
    context
)
```

**Background Process Features:**
- Run long-running commands without blocking
- Monitor output incrementally with BashOutput
- Filter output with regex patterns
- Kill processes when needed
- Each background process gets a unique ID
- Output buffer automatically managed

**AskUserQuestion Usage:**

```python
from minicode.tools.builtin import AskUserQuestionTool

# Define callback to handle questions (for UI/web integration)
async def question_handler(question: str) -> str:
    # Get answer from your UI/web interface
    return user_interface.get_input(question)

# Create tool with callback
ask_tool = AskUserQuestionTool(
    question_callback=question_handler,
    default_timeout=None  # No timeout by default
)

# Agent can ask questions during execution
result = await ask_tool.execute(
    {
        "question": "Which API version should I use?",
        "default_answer": "v2",  # Optional default
        "timeout": 30  # Optional timeout in seconds
    },
    context
)

print(result["answer"])  # User's answer

# CLI mode (no callback - uses stdin)
cli_tool = AskUserQuestionTool()  # Will use input() in thread pool
result = await cli_tool.execute(
    {"question": "Continue with installation?"},
    context
)
```

**AskUserQuestion Features:**
- Support both callback-based and CLI-based interaction
- Multi-round conversations - ask follow-up questions
- Optional timeout with default answers
- Inform agent when user doesn't respond (timeout without default)
- Non-blocking async execution (even for stdin)
- Flexible integration with any UI framework

### 4. MCP Integration

minicode supports [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) for connecting to external tool servers. The configuration format is compatible with Claude Code.

#### Method 1: Agent with MCP Servers (Recommended)

The simplest way to use MCP is through the Agent's built-in support:

```python
import asyncio
from minicode import Agent
from minicode.llm import OpenAILLM

async def main():
    # Configure MCP servers
    mcp_servers = [
        {
            "name": "memory",
            "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
        },
        {
            "name": "filesystem",
            "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"],
        },
    ]

    # Use async context manager for automatic setup/cleanup
    async with Agent(
        name="assistant",
        llm=OpenAILLM(api_key="your-key"),
        mcp_servers=mcp_servers,
    ) as agent:
        # MCP tools are automatically discovered and registered
        async for chunk in agent.stream("Store this note: Hello World"):
            if chunk.get("type") == "content":
                print(chunk.get("content", ""), end="")

asyncio.run(main())
```

#### Method 2: Configuration File

Create a `.minicode/mcp.json` file in your project directory or `~/.minicode/mcp.json` for user-level config:

```json
{
  "mcpServers": {
    "memory": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": {
        "NODE_ENV": "production"
      }
    },
    "api-server": {
      "type": "http",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer your-token"
      }
    }
  }
}
```

The Agent automatically loads MCP servers from config files:

```python
async with Agent(
    name="assistant",
    llm=OpenAILLM(api_key="your-key"),
    # use_global_mcp=True is the default
) as agent:
    # MCP servers from .minicode/mcp.json are automatically loaded
    pass
```

**Config file locations (in order of precedence):**
1. `MINICODE_CONFIG` environment variable
2. `.minicode/mcp.json` in current directory (project-level)
3. `~/.minicode/mcp.json` (user-level config)

To disable automatic config loading:

```python
agent = Agent(
    name="assistant",
    llm=my_llm,
    use_global_mcp=False,  # Don't load from config files
)
```

#### Method 3: Programmatic Global Config

Add MCP servers programmatically to the global config:

```python
from minicode import add_global_mcp_server, Agent

# Add stdio server
add_global_mcp_server(
    name="memory",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-memory"],
    env={"NODE_ENV": "production"},
)

# Add HTTP server
add_global_mcp_server(
    name="api-server",
    url="http://localhost:8080/mcp",
    headers={"Authorization": "Bearer token"},
)

# Agent will automatically use these servers
async with Agent(name="assistant", llm=my_llm) as agent:
    pass
```

#### Method 4: Direct MCPClient Usage

For more control, use MCPClient directly:

```python
from minicode import MCPClient

mcp = MCPClient()

# Add stdio server
await mcp.add_server(
    name="memory",
    command=["npx", "-y", "@modelcontextprotocol/server-memory"],
)

# Add HTTP server
await mcp.add_server(
    name="api",
    url="http://localhost:8080/mcp",
    headers={"Authorization": "Bearer token"},
)

# Get tools and use with agent
tools = mcp.get_tools()
agent = Agent(name="assistant", llm=my_llm, tools=tools)

# Don't forget to cleanup
await mcp.disconnect_all()
```

#### MCP Server Configuration

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier for the server |
| `type` | string | `"stdio"` (default) or `"http"` |
| `command` | string | Command to run (stdio only) |
| `args` | list | Command arguments (stdio only) |
| `url` | string | Server URL (http only) |
| `env` | dict | Environment variables (stdio only) |
| `headers` | dict | HTTP headers (http only) |

#### Popular MCP Servers

- `@modelcontextprotocol/server-memory` - Knowledge graph storage
- `@modelcontextprotocol/server-filesystem` - File system access
- `@modelcontextprotocol/server-github` - GitHub integration
- `@modelcontextprotocol/server-postgres` - PostgreSQL database
- `@modelcontextprotocol/server-sqlite` - SQLite database

See [MCP Servers](https://github.com/modelcontextprotocol/servers) for more options.

### 5. Skills System

Skills provide specialized instructions and workflows for specific tasks. Use the `SkillTool` to access skills:

```python
from minicode.tools.builtin import SkillTool

# Create skill tool (automatically discovers skills)
skill_tool = SkillTool()

# Add to agent
agent.add_tool(skill_tool)

# The agent can now invoke skills by name
# For example: {"skill": "data-analysis"}
```

Skill files should be placed in:
- `.minicode/skills/` (project-specific)
- `~/.minicode/skills/` (user-wide)
- Or set `MINICODE_SKILLS_DIR` environment variable to specify a custom directory

**Skill Format:**

Each skill is a separate directory with a `SKILL.md` file (case-insensitive, e.g., `skill.md` also works, but uppercase is recommended):

```
.minicode/skills/
├── my-skill/              # Directory name is for human readability
│   ├── SKILL.md          # Core skill definition (required)
│   ├── example.py        # Additional files can be referenced
│   └── docs/             # Additional directories can be included
│       └── guide.md
└── another-skill/
    └── SKILL.md
```

**SKILL.md Format:**

```markdown
---
name: my_skill
description: This skill does something useful. Use it when you need to process text input.
---

# Skill Content

This is the main skill content in Markdown format.

You can reference other files in this skill directory:
- See [example.py](./example.py) for implementation details
- Check [guide.md](./docs/guide.md) for usage guide

The agent will selectively read referenced files based on the skill description.
```

**Required YAML metadata fields:**
- `name`: Unique, short, human-readable identifier
- `description`: Natural language description of the skill and when to use it

### 6. Agent Instructions

Agent instructions allow you to define custom instructions that guide agent behavior. These instructions are automatically injected into user messages.

**File locations (in order of precedence):**
1. `MINICODE_AGENT_INSTRUCTIONS` environment variable (path to file, or "0"/"false"/"no"/"off" to disable)
2. `.minicode/AGENT.md` or `.minicode/agent.md` (project-level)
3. `~/.minicode/AGENT.md` or `~/.minicode/agent.md` (user-level)

If both `AGENT.md` and `agent.md` exist in the same directory, `AGENT.md` takes precedence (with a warning).

**Example `.minicode/AGENT.md`:**

```markdown
# Project Guidelines

- Always use Google-style docstrings for code comments
- All generated code must be production-ready
- Ask for clarification if requirements are unclear
- Place test files in the `tests/` directory
```

**Usage:**

```python
# Enabled by default
agent = Agent(
    name="assistant",
    llm=my_llm,
    # use_agent_instructions=True is the default
)

# Disable agent instructions
agent = Agent(
    name="assistant",
    llm=my_llm,
    use_agent_instructions=False,
)
```

**Environment variable control:**

```bash
# Use a custom file
export MINICODE_AGENT_INSTRUCTIONS=/path/to/custom/instructions.md

# Disable agent instructions
export MINICODE_AGENT_INSTRUCTIONS=false
```

## Examples

See the `examples/` directory for complete examples:

- **basic_agent.py** - Interactive agent with file tools
- **custom_llm.py** - Create custom LLM implementations
- **custom_tool.py** - Create custom tools
- **mcp_example.py** - MCP integration examples
- **web_tools_example.py** - WebSearch and WebFetch usage examples
- **notebook_edit_example.py** - Jupyter notebook editing examples
- **todowrite_example.py** - Task management and tracking examples
- **background_process_example.py** - Background process management examples
- **askuserquestion_example.py** - User interaction and question handling examples

## Project Structure

```
minicode/
├── src/minicode/
│   ├── __init__.py          # Main package exports
│   ├── agent.py             # Core Agent implementation
│   ├── llm/
│   │   ├── base.py          # BaseLLM abstract class
│   │   └── openai.py        # OpenAI implementation
│   ├── tools/
│   │   ├── base.py          # BaseTool abstract class
│   │   ├── registry.py      # Tool registry
│   │   └── builtin/         # Built-in tools
│   ├── mcp/
│   │   ├── client.py        # MCP client
│   │   └── transport.py     # Transport layer
│   ├── skills/
│   │   └── loader.py        # Skills loader
│   └── session/
│       ├── message.py       # Message types
│       └── prompt.py        # Prompt management
├── examples/                 # Example scripts
└── tests/                    # Test suite
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/WalterSumbon/minicode-sdk.git
cd minicode

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all unit tests (excludes integration tests)
pytest

# Run with coverage
pytest --cov=minicode

# Run integration tests (makes real API calls)
pytest -m integration

# Run specific test file
pytest tests/test_web_tools.py -v
```

See [tests/README.md](tests/README.md) for detailed testing documentation.

### Code Style

```bash
# Format code
black src/

# Lint code
ruff check src/

# Type check
mypy src/
```

## Design Principles

1. **Simple and Clean** - Code should be easy to understand and modify
2. **Async First** - Built with async/await for efficient operations
3. **Type Safe** - Full type annotations for better IDE support
4. **Extensible** - Easy to add custom LLMs, tools, and integrations
5. **Minimal Dependencies** - Only essential packages included

## Comparison with opencode

| Feature | opencode (TypeScript) | minicode (Python) |
|---------|----------------------|-------------------|
| Language | TypeScript | Python |
| LLM Support | Multiple providers | Extensible (OpenAI included) |
| Tool System | ✅ | ✅ |
| MCP Support | ✅ | ✅ |
| Skills | ✅ | ✅ |
| Async | ✅ | ✅ |
| Type Safety | ✅ | ✅ (with type hints) |

## Roadmap

### Planned Features

- **Advanced Tools**
  - ✅ AskUserQuestion - Interactive user Q&A with timeout and default answer support
  - ✅ Bash - Execute bash commands with timeout support and background execution
  - ✅ BashOutput - Monitor output from background processes
  - ✅ KillShell - Terminate background processes
  - ✅ Glob - File pattern matching tool
  - ✅ Grep - Code search based on ripgrep (with Python fallback)
  - ✅ Edit - Precise string replacement in files
  - ✅ WebFetch - Fetch and process web content (HTML to Markdown/text)
  - ✅ WebSearch - Web search integration (Exa + configurable backends)
  - ✅ NotebookEdit - Jupyter notebook cell editing (replace/insert/delete)

- **Advanced Features**
  - ✅ User Interaction - AskUserQuestion tool for agent-user communication
  - ✅ Background Process Management - BashOutput and KillShell tools for managing long-running processes
  - ✅ Task Management - TodoWrite tool for tracking agent tasks
  - Permission System - Optional callback mechanism for tool execution confirmation
  - File Locking - Prevent concurrent file modification conflicts
  - LSP Integration - Language Server Protocol for code intelligence and diagnostics
  - Multi-Agent System - Task delegation and sub-agent management

### Current Limitations

- No built-in permission/confirmation system (tools execute directly)
- No concurrent file operation protection
- No LSP integration for code diagnostics

These features are intentionally omitted to keep minicode simple and focused. They can be added as optional extensions or in future versions based on community needs.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.