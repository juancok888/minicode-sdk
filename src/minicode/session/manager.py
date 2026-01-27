"""Session manager for creating and retrieving sessions."""

from typing import Dict, List, Optional
from minicode.session.session import Session


class SessionManager:
    """单例管理器，负责创建和检索所有 session.

    这是一个内存存储实现。未来可以扩展为持久化存储。

    Note:
        SessionManager 使用单例模式，确保整个应用中只有一个实例。
        所有方法都是类方法，可以直接通过类名调用。
    """

    _instance: Optional['SessionManager'] = None
    _sessions: Dict[str, Session] = {}

    def __new__(cls):
        """确保单例模式."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def create(
        cls,
        agent_name: str,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Session:
        """创建一个新的 session.

        Args:
            agent_name: Agent 的名称
            parent_id: 父 session ID（用于子 agent）
            metadata: 初始元数据

        Returns:
            新创建的 Session 实例

        Example:
            >>> session = SessionManager.create(agent_name="my_agent")
            >>> print(session.id)
            'a1b2c3d4-...'
        """
        session = Session(
            agent_name=agent_name,
            parent_id=parent_id,
            metadata=metadata or {},
        )
        cls._sessions[session.id] = session
        return session

    @classmethod
    def get(cls, session_id: str) -> Optional[Session]:
        """根据 ID 获取 session.

        Args:
            session_id: Session ID

        Returns:
            Session 实例，如果不存在则返回 None

        Example:
            >>> session = SessionManager.get("a1b2c3d4-...")
            >>> if session:
            ...     print(session.agent_name)
        """
        return cls._sessions.get(session_id)

    @classmethod
    def get_or_raise(cls, session_id: str) -> Session:
        """根据 ID 获取 session，如果不存在则抛出异常.

        Args:
            session_id: Session ID

        Returns:
            Session 实例

        Raises:
            ValueError: 如果 session 不存在

        Example:
            >>> session = SessionManager.get_or_raise("a1b2c3d4-...")
            >>> print(session.agent_name)
        """
        session = cls.get(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        return session

    @classmethod
    def list_all(cls) -> List[Session]:
        """获取所有 session.

        Returns:
            所有 Session 实例的列表

        Example:
            >>> sessions = SessionManager.list_all()
            >>> print(f"Total sessions: {len(sessions)}")
        """
        return list(cls._sessions.values())

    @classmethod
    def get_children(cls, parent_id: str) -> List[Session]:
        """获取指定 session 的所有子 session.

        Args:
            parent_id: 父 session ID

        Returns:
            子 Session 列表

        Example:
            >>> children = SessionManager.get_children("parent-123")
            >>> for child in children:
            ...     print(child.agent_name)
        """
        return [s for s in cls._sessions.values() if s.parent_id == parent_id]

    @classmethod
    def delete(cls, session_id: str) -> bool:
        """删除一个 session.

        Args:
            session_id: 要删除的 session ID

        Returns:
            如果删除成功返回 True，如果 session 不存在返回 False

        Example:
            >>> success = SessionManager.delete("a1b2c3d4-...")
            >>> print(f"Deleted: {success}")
        """
        if session_id in cls._sessions:
            del cls._sessions[session_id]
            return True
        return False

    @classmethod
    def delete_with_children(cls, session_id: str) -> int:
        """删除一个 session 及其所有子 session.

        Args:
            session_id: 要删除的 session ID

        Returns:
            删除的 session 总数（包括自身和所有子 session）

        Example:
            >>> count = SessionManager.delete_with_children("parent-123")
            >>> print(f"Deleted {count} sessions")
        """
        count = 0

        # 递归删除所有子 session
        children = cls.get_children(session_id)
        for child in children:
            count += cls.delete_with_children(child.id)

        # 删除自身
        if cls.delete(session_id):
            count += 1

        return count

    @classmethod
    def clear_all(cls) -> None:
        """清除所有 session（用于测试）.

        Warning:
            这会删除所有 session，包括主 session 和子 session。
            仅在测试或清理时使用。

        Example:
            >>> SessionManager.clear_all()
            >>> assert len(SessionManager.list_all()) == 0
        """
        cls._sessions.clear()

    @classmethod
    def count(cls) -> int:
        """获取当前 session 总数.

        Returns:
            Session 总数

        Example:
            >>> count = SessionManager.count()
            >>> print(f"Total sessions: {count}")
        """
        return len(cls._sessions)

    @classmethod
    def exists(cls, session_id: str) -> bool:
        """检查 session 是否存在.

        Args:
            session_id: Session ID

        Returns:
            如果存在返回 True，否则返回 False

        Example:
            >>> if SessionManager.exists("a1b2c3d4-..."):
            ...     print("Session exists")
        """
        return session_id in cls._sessions
