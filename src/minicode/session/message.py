"""Message types and context for minicode SDK."""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

MessageRole = Literal["system", "user", "assistant", "tool"]

class Message(BaseModel):
    """Represents a message in a conversation."""

    role: MessageRole
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format for LLM APIs."""
        result: Dict[str, Any] = {"role": self.role}

        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id

        if self.content is not None:
            result["content"] = self.content

        if self.tool_calls is not None:
            result["tool_calls"] = self.tool_calls

        return result

class ToolContext(BaseModel):
    """Context passed to tools during execution."""

    agent_name: str = Field(description="Name of the agent executing the tool")
    session_id: Optional[str] = Field(default=None, description="Current session identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from metadata."""
        return self.metadata.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in metadata."""
        self.metadata[key] = value
