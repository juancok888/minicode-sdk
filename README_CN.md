# minicode

一个用于构建 AI Agent 的 Python SDK，支持 LLM、工具、技能和 MCP。

## 概述

**minicode** 是一个简洁、可扩展的 Python AI Agent 构建框架。Minicode 提供了简单而强大的抽象层：

- 🤖 **LLM 集成** - 通过通用接口支持任何 LLM 提供商
- 🛠️ **工具系统** - 可扩展的工具框架，支持 JSON Schema 验证
- 🔌 **MCP 支持** - 连接 Model Context Protocol 服务器以获得更多功能
- 📚 **技能系统** - 从技能目录加载和使用技能
- ⚡ **异步优先** - 基于 async/await 构建，实现高效的 I/O 操作
- 🎯 **类型安全** - 完整的类型注解，提供更好的 IDE 支持

## 安装

```bash
pip install minicode-sdk
```

## 快速开始

> **提示：** 最简单的上手方式是使用 `.minicode/skills/` 目录下的内置技能。只需让你的 AI 编程助手（如 Claude Code）调用 `minicode_usage` 或 `minicode_contributing` 技能，即可帮助你使用 minicode-sdk 进行开发。

### 20 行代码实现 Claude Code

一个生产级的编程助手，支持文件操作、Shell 执行、网络访问、子代理等功能 - 仅需 20 行代码。

查看完整示例：[examples/claude_code_in_20_lines.py](examples/claude_code_in_20_lines.py)

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
# 设置环境变量
export OPENROUTER_API_KEY=your_key
python examples/claude_code_in_20_lines.py
```

## 核心概念

### 1. Agent

`Agent` 类是 minicode 的核心。它结合了 LLM、工具和会话管理：

```python
from minicode import Agent

agent = Agent(
    name="my-agent",
    llm=my_llm,
    tools=[tool1, tool2],
    prompt="System prompt for the agent",
    temperature=0.7,
    top_p=1.0,
    mode="primary",  # 或 "subagent" 或 "all"
)
```

**主要方法：**
- `stream(message)` - 流式获取 agent 的响应
- `generate(message)` - 获取完整响应（非流式）
- `add_tool(tool)` - 向 agent 添加工具
- `reset_session()` - 清除对话历史

### 2. LLM 抽象

minicode 为 LLM 提供商提供了简洁的抽象：

```python
from minicode.llm import BaseLLM

class MyCustomLLM(BaseLLM):
    async def stream(self, messages, tools=None, **kwargs):
        # 实现流式逻辑
        yield {"type": "content", "content": "Hello"}
        yield {"type": "done", "finish_reason": "stop"}

    async def generate(self, messages, **kwargs):
        # 实现非流式逻辑
        return {"content": "Hello", "finish_reason": "stop"}
```

**内置实现：**
- `OpenAILLM` - OpenAI API 集成（GPT-4、GPT-3.5 等）

### 3. 工具系统

工具允许 agent 与环境交互：

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

**内置工具：**
- `AskUserQuestionTool` - 向用户提问并等待回答，支持超时
- `BashTool` - 执行 bash 命令，支持超时和后台执行
- `BashOutputTool` - 监控后台 bash 进程的输出
- `KillShellTool` - 终止后台 bash 进程
- `ReadTool` - 读取文件内容
- `WriteTool` - 写入文件内容
- `EditTool` - 精确的文件字符串替换
- `GlobTool` - 文件模式匹配（如 `**/*.py`）
- `GrepTool` - 基于正则表达式的代码搜索（ripgrep + Python 回退）
- `WebFetchTool` - 获取网页内容，支持 HTML 转 Markdown/文本
- `WebSearchTool` - 网络搜索，支持可配置的后端（Exa、DuckDuckGo）
- `NotebookEditTool` - 编辑 Jupyter notebook 单元格（替换/插入/删除）
- `TodoWriteTool` - 创建和管理结构化任务列表以跟踪进度
- `TaskTool` - 启动子 agent 在隔离会话中处理复杂任务
- `TaskOutputTool` - 子 agent 使用此工具提前返回结果
- `SkillTool` - 从技能目录加载和执行技能
- `ThinkTool` - 记录 agent 的推理和思考过程，提高透明度

**Web 工具使用：**

```python
from minicode.tools.builtin import WebFetchTool, WebSearchTool

# 获取网页内容
webfetch = WebFetchTool()
result = await webfetch.execute(
    {"url": "https://example.com", "format": "markdown"},
    context
)

# 搜索网络
websearch = WebSearchTool(default_backend="exa")
result = await websearch.execute(
    {
        "query": "Python tutorials",
        "num_results": 10,
        "type": "deep",  # Exa 特有：auto、fast 或 deep
        "livecrawl": "preferred"  # Exa 特有：fallback 或 preferred
    },
    context
)
```

**WebFetch 特性：**
- 支持多种输出格式：`text`、`markdown`、`html`
- 使用 html2text 自动将 HTML 转换为 Markdown
- 纯文本提取，移除 script/style
- 可配置超时（默认 30 秒，最大 120 秒）
- 响应大小限制 5MB

**WebSearch 特性：**
- 可配置后端：`exa`（默认）、`duckduckgo`（需要 duckduckgo-search 包）
- Exa 后端支持高级选项：搜索类型（auto/fast/deep）、实时爬取模式
- 可自定义结果数量
- 来自 Exa 的 LLM 优化上下文

**Notebook 工具使用：**

```python
from minicode.tools.builtin import NotebookEditTool

# 替换单元格内容
notebook_tool = NotebookEditTool()
result = await notebook_tool.execute(
    {
        "notebook_path": "/path/to/notebook.ipynb",
        "cell_id": "abc123",
        "new_source": "print('Hello, World!')"
    },
    context
)

# 插入新单元格
result = await notebook_tool.execute(
    {
        "notebook_path": "/path/to/notebook.ipynb",
        "edit_mode": "insert",
        "cell_id": "abc123",  # 在此单元格后插入
        "cell_type": "code",
        "new_source": "x = 42"
    },
    context
)

# 删除单元格
result = await notebook_tool.execute(
    {
        "notebook_path": "/path/to/notebook.ipynb",
        "edit_mode": "delete",
        "cell_id": "abc123",
        "new_source": ""  # 必需但不使用
    },
    context
)
```

**NotebookEdit 特性：**
- 通过单元格 ID 替换单元格内容
- 在任意位置插入新单元格（代码或 markdown）
- 通过 ID 删除单元格
- 更改单元格类型（代码 ↔ markdown）
- 编辑代码单元格时自动清除输出
- 保留 notebook 元数据和结构

**TodoWrite 使用：**

```python
from minicode.tools.builtin import TodoWriteTool

# 创建和管理任务列表
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

**TodoWrite 特性：**
- 跟踪多个任务及其状态（pending/in_progress/completed）
- 每个任务有 `content`（祈使句形式）和 `activeForm`（现在进行时）
- 提供 agent 进度的可见性
- 当多个任务处于 in_progress 时发出警告
- 当存在 pending 任务但没有 in_progress 任务时发出警告
- 帮助组织复杂的多步骤任务

**后台进程工具使用：**

```python
from minicode.tools.builtin import BashTool, BashOutputTool, KillShellTool

# 启动后台进程
bash_tool = BashTool()
result = await bash_tool.execute(
    {
        "command": "python long_running_script.py",
        "run_in_background": True
    },
    context
)

bash_id = result["bash_id"]

# 监控后台进程输出
output_tool = BashOutputTool()
output = await output_tool.execute(
    {
        "bash_id": bash_id,
        "filter": "ERROR|WARNING"  # 可选的正则过滤
    },
    context
)
print(output["output"])  # 仅显示上次检查后的新输出

# 终止后台进程
kill_tool = KillShellTool()
result = await kill_tool.execute(
    {"shell_id": bash_id},
    context
)
```

**后台进程特性：**
- 运行长时间命令而不阻塞
- 使用 BashOutput 增量监控输出
- 使用正则表达式过滤输出
- 需要时终止进程
- 每个后台进程获得唯一 ID
- 输出缓冲区自动管理

**AskUserQuestion 使用：**

```python
from minicode.tools.builtin import AskUserQuestionTool

# 定义处理问题的回调（用于 UI/Web 集成）
async def question_handler(question: str) -> str:
    # 从 UI/Web 界面获取答案
    return user_interface.get_input(question)

# 创建带回调的工具
ask_tool = AskUserQuestionTool(
    question_callback=question_handler,
    default_timeout=None  # 默认无超时
)

# Agent 可以在执行过程中提问
result = await ask_tool.execute(
    {
        "question": "Which API version should I use?",
        "default_answer": "v2",  # 可选的默认答案
        "timeout": 30  # 可选的超时（秒）
    },
    context
)

print(result["answer"])  # 用户的答案

# CLI 模式（无回调 - 使用 stdin）
cli_tool = AskUserQuestionTool()  # 将在线程池中使用 input()
result = await cli_tool.execute(
    {"question": "Continue with installation?"},
    context
)
```

**AskUserQuestion 特性：**
- 支持基于回调和基于 CLI 的交互
- 多轮对话 - 可提出后续问题
- 可选的超时和默认答案
- 当用户不响应时通知 agent（无默认答案的超时）
- 非阻塞异步执行（即使是 stdin）
- 可与任何 UI 框架灵活集成

### 4. MCP 集成

minicode 支持 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)，用于连接外部工具服务器。配置格式与 Claude Code 兼容。

#### 方法 1：Agent 使用 MCP 服务器（推荐）

使用 MCP 最简单的方式是通过 Agent 的内置支持：

```python
import asyncio
from minicode import Agent
from minicode.llm import OpenAILLM

async def main():
    # 配置 MCP 服务器
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

    # 使用异步上下文管理器自动设置/清理
    async with Agent(
        name="assistant",
        llm=OpenAILLM(api_key="your-key"),
        mcp_servers=mcp_servers,
    ) as agent:
        # MCP 工具自动发现并注册
        async for chunk in agent.stream("Store this note: Hello World"):
            if chunk.get("type") == "content":
                print(chunk.get("content", ""), end="")

asyncio.run(main())
```

#### 方法 2：配置文件

在项目目录创建 `.minicode/mcp.json` 文件，或在 `~/.minicode/mcp.json` 创建用户级配置：

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

Agent 自动从配置文件加载 MCP 服务器：

```python
async with Agent(
    name="assistant",
    llm=OpenAILLM(api_key="your-key"),
    # use_global_mcp=True 是默认值
) as agent:
    # .minicode/mcp.json 中的 MCP 服务器自动加载
    pass
```

**配置文件位置（按优先级）：**
1. `MINICODE_CONFIG` 环境变量
2. 当前目录的 `.minicode/mcp.json`（项目级配置）
3. `~/.minicode/mcp.json`（用户级配置）

禁用自动配置加载：

```python
agent = Agent(
    name="assistant",
    llm=my_llm,
    use_global_mcp=False,  # 不从配置文件加载
)
```

#### 方法 3：编程式全局配置

以编程方式向全局配置添加 MCP 服务器：

```python
from minicode import add_global_mcp_server, Agent

# 添加 stdio 服务器
add_global_mcp_server(
    name="memory",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-memory"],
    env={"NODE_ENV": "production"},
)

# 添加 HTTP 服务器
add_global_mcp_server(
    name="api-server",
    url="http://localhost:8080/mcp",
    headers={"Authorization": "Bearer token"},
)

# Agent 将自动使用这些服务器
async with Agent(name="assistant", llm=my_llm) as agent:
    pass
```

#### 方法 4：直接使用 MCPClient

需要更多控制时，直接使用 MCPClient：

```python
from minicode import MCPClient

mcp = MCPClient()

# 添加 stdio 服务器
await mcp.add_server(
    name="memory",
    command=["npx", "-y", "@modelcontextprotocol/server-memory"],
)

# 添加 HTTP 服务器
await mcp.add_server(
    name="api",
    url="http://localhost:8080/mcp",
    headers={"Authorization": "Bearer token"},
)

# 获取工具并与 agent 一起使用
tools = mcp.get_tools()
agent = Agent(name="assistant", llm=my_llm, tools=tools)

# 别忘了清理
await mcp.disconnect_all()
```

#### MCP 服务器配置

| 字段 | 类型 | 描述 |
|------|------|------|
| `name` | string | 服务器的唯一标识符 |
| `type` | string | `"stdio"`（默认）或 `"http"` |
| `command` | string | 要运行的命令（仅 stdio） |
| `args` | list | 命令参数（仅 stdio） |
| `url` | string | 服务器 URL（仅 http） |
| `env` | dict | 环境变量（仅 stdio） |
| `headers` | dict | HTTP 头（仅 http） |

#### 常用 MCP 服务器

- `@modelcontextprotocol/server-memory` - 知识图谱存储
- `@modelcontextprotocol/server-filesystem` - 文件系统访问
- `@modelcontextprotocol/server-github` - GitHub 集成
- `@modelcontextprotocol/server-postgres` - PostgreSQL 数据库
- `@modelcontextprotocol/server-sqlite` - SQLite 数据库

更多选项请参见 [MCP Servers](https://github.com/modelcontextprotocol/servers)。

### 5. 技能系统

技能为特定任务提供专门的指令和工作流。使用 `SkillTool` 访问技能：

```python
from minicode.tools.builtin import SkillTool

# 创建技能工具（自动发现技能）
skill_tool = SkillTool()

# 添加到 agent
agent.add_tool(skill_tool)

# Agent 现在可以按名称调用技能
# 例如：{"skill": "data-analysis"}
```

技能文件应放置在：
- `.minicode/skills/`（项目特定）
- `~/.minicode/skills/`（用户级）
- 或设置 `MINICODE_SKILLS_DIR` 环境变量指定自定义目录

**技能格式：**

每个技能是一个包含 `SKILL.md` 文件的独立目录（不区分大小写，如 `skill.md` 也可以，但推荐使用大写）：

```
.minicode/skills/
├── my-skill/              # 目录名用于人类可读性
│   ├── SKILL.md          # 核心技能定义（必需）
│   ├── example.py        # 可以引用的附加文件
│   └── docs/             # 可以包含的附加目录
│       └── guide.md
└── another-skill/
    └── SKILL.md
```

**SKILL.md 格式：**

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

**必需的 YAML 元数据字段：**
- `name`：唯一的、简短的、人类可读的标识符
- `description`：技能的自然语言描述及其使用场景

### 6. Agent 指令

Agent 指令允许你定义自定义指令来指导 agent 的行为。这些指令会自动注入到用户消息中。

**文件位置（按优先级）：**
1. `MINICODE_AGENT_INSTRUCTIONS` 环境变量（文件路径，或 "0"/"false"/"no"/"off" 禁用）
2. `.minicode/AGENT.md` 或 `.minicode/agent.md`（项目级）
3. `~/.minicode/AGENT.md` 或 `~/.minicode/agent.md`（用户级）

如果同一目录下同时存在 `AGENT.md` 和 `agent.md`，将优先使用 `AGENT.md`（并输出警告）。

**示例 `.minicode/AGENT.md`：**

```markdown
# 项目规范

- 代码注释使用 Google 风格
- 所有生成的代码必须可直接投入生产环境
- 如果需求不明确，先询问用户
- 测试文件放在 `tests/` 目录下
```

**使用方法：**

```python
# 默认启用
agent = Agent(
    name="assistant",
    llm=my_llm,
    # use_agent_instructions=True 是默认值
)

# 禁用 agent 指令
agent = Agent(
    name="assistant",
    llm=my_llm,
    use_agent_instructions=False,
)
```

**环境变量控制：**

```bash
# 使用自定义文件
export MINICODE_AGENT_INSTRUCTIONS=/path/to/custom/instructions.md

# 禁用 agent 指令
export MINICODE_AGENT_INSTRUCTIONS=false
```

## 示例

查看 `examples/` 目录获取完整示例：

- **basic_agent.py** - 带文件工具的交互式 agent
- **custom_llm.py** - 创建自定义 LLM 实现
- **custom_tool.py** - 创建自定义工具
- **mcp_example.py** - MCP 集成示例
- **web_tools_example.py** - WebSearch 和 WebFetch 使用示例
- **notebook_edit_example.py** - Jupyter notebook 编辑示例
- **todowrite_example.py** - 任务管理和跟踪示例
- **background_process_example.py** - 后台进程管理示例
- **askuserquestion_example.py** - 用户交互和问题处理示例

## 项目结构

```
minicode/
├── src/minicode/
│   ├── __init__.py          # 主包导出
│   ├── agent.py             # 核心 Agent 实现
│   ├── llm/
│   │   ├── base.py          # BaseLLM 抽象类
│   │   └── openai.py        # OpenAI 实现
│   ├── tools/
│   │   ├── base.py          # BaseTool 抽象类
│   │   ├── registry.py      # 工具注册表
│   │   └── builtin/         # 内置工具
│   ├── mcp/
│   │   ├── client.py        # MCP 客户端
│   │   └── transport.py     # 传输层
│   ├── skills/
│   │   └── loader.py        # 技能加载器
│   └── session/
│       ├── message.py       # 消息类型
│       └── prompt.py        # 提示词管理
├── examples/                 # 示例脚本
└── tests/                    # 测试套件
```

## 开发

### 设置

```bash
# 克隆仓库
git clone https://github.com/WalterSumbon/minicode-sdk.git
cd minicode

# 以开发模式安装
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有单元测试（排除集成测试）
pytest

# 运行带覆盖率的测试
pytest --cov=minicode

# 运行集成测试（会进行真实 API 调用）
pytest -m integration

# 运行特定测试文件
pytest tests/test_web_tools.py -v
```

详细的测试文档请参见 [tests/README.md](tests/README.md)。

### 代码风格

```bash
# 格式化代码
black src/

# 代码检查
ruff check src/

# 类型检查
mypy src/
```

## 设计原则

1. **简洁明了** - 代码应易于理解和修改
2. **异步优先** - 基于 async/await 构建，实现高效操作
3. **类型安全** - 完整的类型注解，提供更好的 IDE 支持
4. **可扩展** - 易于添加自定义 LLM、工具和集成
5. **最小依赖** - 仅包含必要的包

## 与 opencode 的比较

| 特性 | opencode (TypeScript) | minicode (Python) |
|------|----------------------|-------------------|
| 语言 | TypeScript | Python |
| LLM 支持 | 多提供商 | 可扩展（包含 OpenAI） |
| 工具系统 | ✅ | ✅ |
| MCP 支持 | ✅ | ✅ |
| 技能 | ✅ | ✅ |
| 异步 | ✅ | ✅ |
| 类型安全 | ✅ | ✅（使用类型提示） |

## 路线图

### 计划中的功能

- **高级工具**
  - ✅ AskUserQuestion - 支持超时和默认答案的交互式用户问答
  - ✅ Bash - 支持超时和后台执行的 bash 命令执行
  - ✅ BashOutput - 监控后台进程输出
  - ✅ KillShell - 终止后台进程
  - ✅ Glob - 文件模式匹配工具
  - ✅ Grep - 基于 ripgrep 的代码搜索（带 Python 回退）
  - ✅ Edit - 精确的文件字符串替换
  - ✅ WebFetch - 获取和处理网页内容（HTML 转 Markdown/文本）
  - ✅ WebSearch - 网络搜索集成（Exa + 可配置后端）
  - ✅ NotebookEdit - Jupyter notebook 单元格编辑（替换/插入/删除）

- **高级功能**
  - ✅ 用户交互 - AskUserQuestion 工具用于 agent-用户通信
  - ✅ 后台进程管理 - BashOutput 和 KillShell 工具用于管理长时间运行的进程
  - ✅ 任务管理 - TodoWrite 工具用于跟踪 agent 任务
  - 权限系统 - 工具执行确认的可选回调机制
  - 文件锁定 - 防止并发文件修改冲突
  - LSP 集成 - 语言服务器协议用于代码智能和诊断
  - 多 Agent 系统 - 任务委派和子 agent 管理

### 当前限制

- 无内置权限/确认系统（工具直接执行）
- 无并发文件操作保护
- 无代码诊断的 LSP 集成

这些功能被有意省略以保持 minicode 的简单和专注。它们可以作为可选扩展添加，或根据社区需求在未来版本中添加。

## 贡献

欢迎贡献！请随时提交 Pull Request。

## 许可证

MIT 许可证 - 详见 LICENSE 文件。
