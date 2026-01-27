---
name: minicode_contributing
description: Guide for contributing to the minicode-sdk project. Use this skill when the user wants to contribute code, fix bugs, add features, or improve documentation for the minicode-sdk project.
---

# Contributing to minicode-sdk

## Project Structure

```
minicode-sdk/
├── src/minicode/           # Main source code
│   ├── __init__.py         # Package exports
│   ├── agent.py            # Core Agent implementation
│   ├── config.py           # Global configuration (MCP, Agent Instructions)
│   ├── llm/                # LLM implementations
│   │   ├── base.py         # BaseLLM abstract class
│   │   └── openai.py       # OpenAI implementation
│   ├── tools/              # Tool system
│   │   ├── base.py         # BaseTool abstract class
│   │   ├── registry.py     # Tool registry
│   │   └── builtin/        # Built-in tools
│   ├── mcp/                # MCP integration
│   │   ├── client.py       # MCP client
│   │   └── transport.py    # Transport layer
│   ├── skills/             # Skills system
│   │   └── loader.py       # Skills loader
│   └── session/            # Session management
│       ├── message.py      # Message types
│       ├── session.py      # Session class
│       ├── manager.py      # Session manager
│       └── prompt.py       # Prompt management
├── tests/                  # Test suite
├── examples/               # Example scripts
├── .minicode/              # Project configuration
│   ├── mcp.json            # MCP server config
│   ├── AGENT.md            # Agent instructions
│   └── skills/             # Project skills
└── docs/                   # Documentation
```

## Configuration Files

The `.minicode/` directory contains project-level configurations:

- `mcp.json` - MCP server configurations
- `AGENT.md` - Agent behavior instructions
- `skills/` - Custom skills for the project

## Code Style Guidelines

1. **Docstrings**: Use Google-style docstrings for all public functions and classes
2. **Type hints**: All function parameters and return values must have type annotations
3. **Comments**: Use English for code comments
4. **Imports**: Group imports in order: standard library, third-party, local

## Adding New Features

### Adding a New Tool

1. Create a new file in `src/minicode/tools/builtin/`
2. Inherit from `BaseTool`
3. Implement required methods: `name`, `description`, `parameters`, `execute`
4. Export in `src/minicode/tools/builtin/__init__.py`

### Adding a New LLM Provider

1. Create a new file in `src/minicode/llm/`
2. Inherit from `BaseLLM`
3. Implement required methods: `stream`, `generate`
4. Export in `src/minicode/llm/__init__.py`

## Testing

- All tests should be placed in `tests/` directory
- Run tests with: `pytest tests/`
- Ensure all tests pass before submitting PR

## Pull Request Process

1. Create a feature branch from `main`
2. Make changes following the code style guidelines
3. Add tests for new functionality
4. Update documentation if needed
5. Submit PR with clear description of changes
