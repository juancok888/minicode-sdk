"""Session abstraction for managing conversation state."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

from minicode.session.message import Message


class Session(BaseModel):
    """代表一个会话（conversation）实例.

    Session 封装了 agent 运行所需的所有状态，包括消息历史、元数据等。
    支持父子关系（用于 Task 工具创建的子 agent session）。

    Attributes:
        id: 唯一会话标识符
        parent_id: 父 session ID（用于子 agent）
        agent_name: 使用此 session 的 agent 名称
        messages: 消息历史列表
        metadata: 额外元数据字典
        created_at: 创建时间
        updated_at: 最后更新时间
        completed: 任务是否已完成（用于 Task）
        result: 任务结果（用于 Task）
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = Field(default=None, description="Parent session ID for sub-agents")
    agent_name: str = Field(description="Name of the agent using this session")

    # 消息历史
    messages: List[Message] = Field(default_factory=list)

    # 元数据（用于扩展，如 todo 列表、权限规则等）
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Task 相关（用于子 agent）
    completed: bool = Field(default=False, description="Whether task is completed")
    result: Optional[str] = Field(default=None, description="Task result if completed")

    class Config:
        """Pydantic 配置."""
        arbitrary_types_allowed = True

    def add_message(self, message: Message) -> None:
        """添加消息到会话历史.

        Args:
            message: 要添加的消息
        """
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_messages_dict(self) -> List[Dict[str, Any]]:
        """获取消息的字典格式（用于 LLM API）.

        Returns:
            消息列表的字典格式
        """
        return [msg.to_dict() for msg in self.messages]

    def clear_messages(self) -> None:
        """清空消息历史（保留 system message）."""
        system_messages = [msg for msg in self.messages if msg.role == "system"]
        self.messages = system_messages
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于序列化）.

        Returns:
            Session 的字典表示
        """
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "agent_name": self.agent_name,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed": self.completed,
            "result": self.result,
            "message_count": len(self.messages),
        }

    def __repr__(self) -> str:
        """字符串表示."""
        return (
            f"Session(id={self.id[:8]}..., agent={self.agent_name}, "
            f"messages={len(self.messages)}, completed={self.completed})"
        )
