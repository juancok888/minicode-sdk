"""TaskOutput tool for sub-agents to return results."""

from typing import Any, Dict, Optional

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool


class TaskCompletedSignal(Exception):
    """子 agent 通过 TaskOutput 工具完成任务的信号.

    这是一个特殊的异常，用于在子 agent 调用 TaskOutput 工具时
    终止 agent 的运行循环并返回结果。

    Attributes:
        result: 任务结果文本
        metadata: 附加的结构化元数据
    """

    def __init__(self, result: str, metadata: Optional[Dict[str, Any]] = None):
        """初始化 TaskCompletedSignal.

        Args:
            result: 任务结果文本
            metadata: 可选的结构化元数据
        """
        self.result = result
        self.metadata = metadata or {}
        super().__init__("Task completed via TaskOutput tool")


class TaskOutputTool(BaseTool):
    """子 agent 用于返回结果的工具.

    TaskOutput 工具允许子 agent 主动控制何时完成任务并返回结果。
    调用此工具会抛出 TaskCompletedSignal 异常，由 Task 工具捕获。

    Note:
        - 这个工具是可选的：子 agent 可以选择调用或不调用
        - 如果调用，Task 工具会使用 TaskOutput 中的结果
        - 如果不调用，Task 工具会使用子 agent 最后一轮的全部文本作为结果
    """

    @property
    def name(self) -> str:
        """工具名称."""
        return "taskoutput"

    @property
    def description(self) -> str:
        """工具描述."""
        return """Return the final result of your task to the parent agent.

IMPORTANT: When you have completed your task, you MUST call this tool to return results.
This signals task completion and allows you to return structured data.

If you don't call this tool, your entire final response will be used as the result.

Usage:
- Call this tool when you have finished your task
- Provide a clear, complete summary in the 'result' field
- Optionally include structured data in the 'metadata' field

Example:
{
  "result": "Found 5 API endpoints in src/api/. Main endpoints: /users, /posts, /comments...",
  "metadata": {
    "file_count": 3,
    "endpoint_count": 5,
    "files": ["src/api/users.py", "src/api/posts.py", "src/api/comments.py"]
  }
}"""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """参数 schema."""
        return {
            "type": "object",
            "properties": {
                "result": {
                    "type": "string",
                    "description": "The final result to return to the parent agent. Should be a clear, complete summary of your findings."
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional structured metadata to include with the result (e.g., file counts, paths, statistics)",
                    "additionalProperties": True
                }
            },
            "required": ["result"]
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """执行 TaskOutput 工具.

        此方法会抛出 TaskCompletedSignal 异常来终止子 agent 的运行。
        Task 工具会捕获这个异常并提取结果。

        Args:
            params: 工具参数，包含 'result' 和可选的 'metadata'
            context: 工具执行上下文

        Returns:
            永远不会正常返回，总是抛出 TaskCompletedSignal

        Raises:
            TaskCompletedSignal: 携带任务结果的信号异常
        """
        result = params["result"]
        metadata = params.get("metadata", {})

        # 抛出信号以终止 agent 循环
        raise TaskCompletedSignal(result, metadata)
