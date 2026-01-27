"""Task tool for launching sub-agents."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from minicode.agent_registry import AgentRegistry
from minicode.session.manager import SessionManager
from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool
from minicode.tools.builtin.taskoutput import TaskOutputTool, TaskCompletedSignal

if TYPE_CHECKING:
    from minicode.agent import Agent


class TaskTool(BaseTool):
    """启动子 agent 处理复杂任务的工具.

    Task 工具允许主 agent 将复杂的、多步骤的任务委托给专门的子 agent。
    子 agent 在独立的 session 中运行，完成后返回结果。

    工作流程:
    1. 主 agent 调用 Task 工具，指定 subagent_type 和 prompt
    2. Task 工具创建新的 session（或恢复已有 session）
    3. 创建子 agent 实例，配置工具访问权限
    4. 运行子 agent 直到完成
    5. 返回结果（优先使用 TaskOutput 的结果，否则使用最后的文本）

    Attributes:
        parent_agent: 父 agent 实例（用于传递 LLM、工具等）
    """

    def __init__(self, parent_agent: Optional["Agent"] = None):
        """初始化 Task 工具.

        Args:
            parent_agent: 父 agent 实例（用于传递 LLM、工具等）。
                         如果为 None，将在 execute 时从 context 中获取。
        """
        self.parent_agent = parent_agent

    @property
    def name(self) -> str:
        """工具名称."""
        return "task"

    @property
    def description(self) -> str:
        """工具描述（动态生成，包含可用的 subagent 列表）."""
        subagents = AgentRegistry.list(mode="subagent")
        if not subagents:
            subagent_list = "(No subagents available)"
        else:
            subagent_list = "\n".join([
                f"- {a.name}: {a.description or 'No description'}"
                for a in subagents
            ])

        return f"""Launch a new agent to handle complex, multi-step tasks autonomously.

Available subagent types:
{subagent_list}

Usage notes:
1. Use this tool when you need to delegate a complex task to a specialized agent
2. Each subagent runs in an isolated session with limited tool access
3. Subagents can optionally call TaskOutput to return results early
4. You can resume a previous subagent session by providing session_id

When NOT to use:
- For simple file reads (use Read tool instead)
- For single grep/glob operations (use those tools directly)
- For tasks that don't match any subagent's specialty

Example:
{{
  "description": "Search codebase for API endpoints",
  "prompt": "Find all API endpoint definitions in the src/ directory. Look for route decorators, URL patterns, etc.",
  "subagent_type": "explore"
}}"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """参数 schema."""
        subagent_names = [a.name for a in AgentRegistry.list(mode="subagent")]

        return {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "A short (3-5 words) description of the task"
                },
                "prompt": {
                    "type": "string",
                    "description": "Detailed instructions for the subagent to perform"
                },
                "subagent_type": {
                    "type": "string",
                    "description": "The type of specialized agent to use",
                    "enum": subagent_names if subagent_names else ["explore", "general"]
                },
                "session_id": {
                    "type": "string",
                    "description": "Optional: ID of existing session to resume"
                },
            },
            "required": ["description", "prompt", "subagent_type"]
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """执行 Task 工具.

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            包含子 agent 结果的字典，格式为:
            {
                "success": True,
                "title": "任务描述",
                "output": "结果文本",
                "metadata": {
                    "session_id": "...",
                    "used_taskoutput": True/False,
                    ...
                }
            }
        """
        # Get parent agent from context if not set during init
        parent_agent = self.parent_agent
        if parent_agent is None:
            parent_agent = context.metadata.get("_agent")
            if parent_agent is None:
                return {
                    "success": False,
                    "error": "TaskTool requires parent_agent reference (not found in context)"
                }

        description = params["description"]
        prompt = params["prompt"]
        subagent_type = params["subagent_type"]
        session_id = params.get("session_id")

        # 1. 获取子 agent 配置
        agent_config = AgentRegistry.get(subagent_type)
        if not agent_config:
            available = [a.name for a in AgentRegistry.list(mode="subagent")]
            return {
                "success": False,
                "error": f"Unknown subagent type: {subagent_type}. Available: {available}"
            }

        # 检查是否允许作为 subagent
        if agent_config.mode == "primary":
            return {
                "success": False,
                "error": f"Agent '{subagent_type}' cannot be used as a subagent (mode={agent_config.mode})"
            }

        # 2. 创建或获取 session
        if session_id:
            session = SessionManager.get(session_id)
            if not session:
                return {
                    "success": False,
                    "error": f"Session not found: {session_id}"
                }
        else:
            # 创建新 session
            session = SessionManager.create(
                agent_name=subagent_type,
                parent_id=context.session_id,
                metadata={
                    "task_description": description,
                    "parent_agent": parent_agent.name,
                }
            )

        # 3. 创建子 agent
        # 延迟导入以避免循环依赖
        from minicode.agent import Agent

        subagent = Agent(
            name=agent_config.name,
            llm=parent_agent.llm,  # 继承父 agent 的 LLM
            system_prompt=agent_config.prompt,
            mode=agent_config.mode,
            temperature=agent_config.temperature or parent_agent.temperature,
            top_p=agent_config.top_p or parent_agent.top_p,
            max_tokens=agent_config.max_tokens or parent_agent.max_tokens,
            session=session,  # 使用创建的 session
        )

        # 4. 添加工具（根据 agent_config 过滤）
        allowed_tools = self._get_allowed_tools(agent_config, parent_agent)
        for tool in allowed_tools:
            subagent.add_tool(tool)

        # 5. 必须添加 TaskOutput 工具
        subagent.add_tool(TaskOutputTool())

        # 6. 运行子 agent
        try:
            # 收集所有文本输出
            text_chunks: List[str] = []

            async for chunk in subagent.stream(prompt):
                chunk_type = chunk.get("type")

                if chunk_type == "content":
                    text_chunks.append(chunk.get("content", ""))

                elif chunk_type == "done":
                    # 子 agent 完成但没有调用 TaskOutput
                    # Fallback：使用所有文本作为结果
                    full_text = "".join(text_chunks)
                    session.completed = True
                    session.result = full_text

                    return {
                        "success": True,
                        "title": description,
                        "output": full_text,
                        "metadata": {
                            "session_id": session.id,
                            "used_taskoutput": False,
                        }
                    }

        except TaskCompletedSignal as signal:
            # 子 agent 调用了 TaskOutput
            session.completed = True
            session.result = signal.result
            session.metadata.update(signal.metadata)

            return {
                "success": True,
                "title": description,
                "output": signal.result,
                "metadata": {
                    "session_id": session.id,
                    "used_taskoutput": True,
                    **signal.metadata
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Subagent execution failed: {str(e)}",
                "session_id": session.id,
            }

        # 不应该到达这里
        return {
            "success": False,
            "error": "Unexpected execution path",
            "session_id": session.id,
        }

    def _get_allowed_tools(self, agent_config, parent_agent: "Agent") -> List[BaseTool]:
        """根据 agent 配置获取允许的工具列表.

        工具过滤规则:
        1. 始终拒绝 'task' 工具（防止递归）
        2. 始终拒绝 'todowrite' 和 'todoread'（避免干扰主 agent）
        3. 如果工具在 denied_tools 中，拒绝
        4. 如果指定了 allowed_tools，只允许列表中的工具（但跳过 taskoutput，因为它会单独添加）

        Args:
            agent_config: Agent 配置
            parent_agent: 父 agent 实例

        Returns:
            允许的工具列表
        """
        # 从父 agent 获取所有工具
        all_tools = parent_agent.tool_registry.get_all()

        # 过滤工具
        allowed = []
        for tool in all_tools:
            tool_name = tool.name

            # 始终禁止子 agent 使用 Task 工具（防止递归）
            if tool_name == "task":
                continue

            # 始终禁止 TodoWrite/TodoRead（避免干扰主 agent）
            if tool_name in ["todowrite", "todoread"]:
                continue

            # 检查是否在 denied_tools 列表中
            if tool_name in agent_config.denied_tools:
                continue

            # 检查是否在 allowed_tools 列表中（如果指定了）
            # 注意：跳过 taskoutput，因为它会在外部单独添加
            if agent_config.allowed_tools is not None:
                if tool_name == "taskoutput":
                    continue  # 跳过，外部会添加
                if tool_name not in agent_config.allowed_tools:
                    continue

            allowed.append(tool)

        return allowed
