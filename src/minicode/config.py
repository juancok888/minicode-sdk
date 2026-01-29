"""Global configuration management for minicode.

This module handles loading and managing global configuration, including
MCP server configurations and agent instructions from config files.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Project-level config directory (relative to current directory)
PROJECT_CONFIG_DIR = ".minicode"

# User-level config directory (relative to home directory)
USER_CONFIG_DIR = ".minicode"

# MCP config file name
MCP_CONFIG_FILE = "mcp.json"

# Agent instructions file names (case variations, AGENT.md takes precedence)
AGENT_INSTRUCTIONS_FILES = ["AGENT.md", "agent.md"]

# Environment variables
CONFIG_ENV_VAR = "MINICODE_CONFIG"
AGENT_INSTRUCTIONS_ENV_VAR = "MINICODE_AGENT_INSTRUCTIONS"


class MCPConfig:
    """Global MCP configuration manager.

    This class handles loading MCP server configurations from:
    1. Environment variable MINICODE_CONFIG pointing to a config file
    2. Project-level config file (.minicode/mcp.json)
    3. User-level config file (~/.minicode/mcp.json)

    Config file format (JSON):
    {
        "mcpServers": {
            "memory": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"],
                "env": {"KEY": "value"}
            },
            "remote": {
                "type": "http",
                "url": "http://localhost:8080/mcp",
                "headers": {"Authorization": "Bearer token"}
            }
        }
    }
    """

    _instance: Optional["MCPConfig"] = None
    _servers: List[Dict[str, Any]]
    _loaded: bool

    def __new__(cls) -> "MCPConfig":
        """Singleton pattern to ensure only one config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._servers = []
            cls._instance._loaded = False
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None

    def _find_config_file(self) -> Optional[Path]:
        """Find the first available config file.

        Returns:
            Path to config file if found, None otherwise.
        """
        # Check environment variable first
        env_path = os.environ.get(CONFIG_ENV_VAR)
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path

        # Check current directory for project-level config
        project_config = Path.cwd() / PROJECT_CONFIG_DIR / MCP_CONFIG_FILE
        if project_config.exists():
            return project_config

        # Check home directory for user-level config
        home_config = Path.home() / USER_CONFIG_DIR / MCP_CONFIG_FILE
        if home_config.exists():
            return home_config

        return None

    def load(self, force: bool = False) -> None:
        """Load MCP configuration from config file.

        Args:
            force: If True, reload even if already loaded.
        """
        if self._loaded and not force:
            return

        self._servers = []
        config_file = self._find_config_file()

        if config_file:
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # Parse mcpServers object (Claude Code format)
                mcp_servers = config.get("mcpServers", {})
                if isinstance(mcp_servers, dict):
                    self._servers = self._parse_mcp_servers(mcp_servers)

            except (json.JSONDecodeError, IOError):
                # Invalid config file, use empty config
                pass

        self._loaded = True

    def _parse_mcp_servers(
        self, mcp_servers: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse mcpServers object into internal format.

        Args:
            mcp_servers: Dict with server names as keys.

        Returns:
            List of server configurations in internal format.
        """
        servers = []
        for name, config in mcp_servers.items():
            server: Dict[str, Any] = {"name": name}

            server_type = config.get("type", "stdio")

            if server_type == "stdio":
                # Build command list from command + args
                command = config.get("command")
                args = config.get("args", [])
                if command:
                    server["command"] = [command] + args
                if config.get("env"):
                    server["env"] = config["env"]
            elif server_type == "http":
                if config.get("url"):
                    server["url"] = config["url"]
                if config.get("headers"):
                    server["headers"] = config["headers"]

            servers.append(server)

        return servers

    def get_servers(self) -> List[Dict[str, Any]]:
        """Get the list of configured MCP servers.

        Returns:
            List of MCP server configurations.
        """
        if not self._loaded:
            self.load()
        return self._servers.copy()

    def add_server(self, server_config: Dict[str, Any]) -> None:
        """Add a server configuration programmatically.

        Args:
            server_config: Server configuration dictionary.
        """
        if not self._loaded:
            self.load()
        self._servers.append(server_config)

    def clear_servers(self) -> None:
        """Clear all server configurations."""
        self._servers = []


def get_global_mcp_servers() -> List[Dict[str, Any]]:
    """Get the global MCP server configurations.

    This is a convenience function to get MCP servers from the global config.

    Returns:
        List of MCP server configurations.
    """
    return MCPConfig().get_servers()


def add_global_mcp_server(
    name: str,
    command: Optional[str] = None,
    args: Optional[List[str]] = None,
    url: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> None:
    """Add an MCP server to the global configuration.

    Args:
        name: Server name identifier.
        command: Command for stdio transport (mutually exclusive with url).
        args: Arguments for the command.
        url: URL for HTTP transport (mutually exclusive with command).
        env: Environment variables for stdio transport.
        headers: Headers for HTTP transport.
    """
    config: Dict[str, Any] = {"name": name}

    if command:
        # Build command list from command + args (internal format)
        config["command"] = [command] + (args or [])
    if url:
        config["url"] = url
    if env:
        config["env"] = env
    if headers:
        config["headers"] = headers

    MCPConfig().add_server(config)


class AgentInstructionsConfig:
    """Agent instructions configuration manager.

    This class handles loading agent instructions from:
    1. Environment variable MINICODE_AGENT_INSTRUCTIONS pointing to a file
    2. Project-level file (.minicode/AGENT.md or .minicode/agent.md)
    3. User-level file (~/.minicode/AGENT.md or ~/.minicode/agent.md)

    Priority: project-level > user-level
    File name priority: AGENT.md > agent.md (warns if both exist)
    """

    _instance: Optional["AgentInstructionsConfig"] = None
    _instructions: Optional[str]
    _loaded: bool
    _source_path: Optional[Path]

    def __new__(cls) -> "AgentInstructionsConfig":
        """Singleton pattern to ensure only one config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._instructions = None
            cls._instance._loaded = False
            cls._instance._source_path = None
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None

    def _find_instructions_file_in_dir(
        self, base_dir: Path
    ) -> Tuple[Optional[Path], bool]:
        """Find agent instructions file in a directory.

        Args:
            base_dir: Base directory to search in.

        Returns:
            Tuple of (path to file if found, whether both variants exist).
        """
        config_dir = base_dir / PROJECT_CONFIG_DIR
        if not config_dir.exists():
            return None, False

        upper_path = config_dir / "AGENT.md"
        lower_path = config_dir / "agent.md"

        upper_exists = upper_path.exists()
        lower_exists = lower_path.exists()

        if upper_exists and lower_exists:
            return upper_path, True
        elif upper_exists:
            return upper_path, False
        elif lower_exists:
            return lower_path, False

        return None, False

    def _find_instructions_file(self) -> Optional[Path]:
        """Find the agent instructions file.

        Returns:
            Path to instructions file if found, None otherwise.
        """
        # Check environment variable first
        env_path = os.environ.get(AGENT_INSTRUCTIONS_ENV_VAR)
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path

        # Check project-level first (higher priority)
        project_file, both_exist = self._find_instructions_file_in_dir(Path.cwd())
        if both_exist:
            config_dir = Path.cwd() / PROJECT_CONFIG_DIR
            logger.warning(
                "Multiple agent instruction files detected:\n"
                "  - %s\n"
                "  - %s\n"
                "Selected: %s",
                config_dir / "AGENT.md",
                config_dir / "agent.md",
                project_file,
            )
        if project_file:
            return project_file

        # Check user-level
        user_file, both_exist = self._find_instructions_file_in_dir(Path.home())
        if both_exist:
            config_dir = Path.home() / USER_CONFIG_DIR
            logger.warning(
                "Multiple agent instruction files detected:\n"
                "  - %s\n"
                "  - %s\n"
                "Selected: %s",
                config_dir / "AGENT.md",
                config_dir / "agent.md",
                user_file,
            )
        if user_file:
            return user_file

        return None

    def load(self, force: bool = False) -> None:
        """Load agent instructions from file.

        Args:
            force: If True, reload even if already loaded.
        """
        if self._loaded and not force:
            return

        self._instructions = None
        self._source_path = self._find_instructions_file()

        if self._source_path:
            try:
                with open(self._source_path, "r", encoding="utf-8") as f:
                    self._instructions = f.read()
            except IOError:
                pass

        self._loaded = True

    def get_instructions(self) -> Optional[str]:
        """Get the agent instructions content.

        Returns:
            Instructions content if found, None otherwise.
        """
        if not self._loaded:
            self.load()
        return self._instructions

    def get_source_path(self) -> Optional[Path]:
        """Get the source path of the loaded instructions.

        Returns:
            Path to the instructions file if loaded, None otherwise.
        """
        if not self._loaded:
            self.load()
        return self._source_path


def get_agent_instructions() -> Optional[str]:
    """Get the global agent instructions.

    This is a convenience function to get agent instructions from the global config.

    Returns:
        Agent instructions content if found, None otherwise.
    """
    return AgentInstructionsConfig().get_instructions()


def is_agent_instructions_enabled() -> bool:
    """Check if agent instructions loading is enabled via environment variable.

    The MINICODE_AGENT_INSTRUCTIONS environment variable can be set to:
    - A file path: enables and uses that file
    - "0", "false", "no", "off": disables agent instructions
    - Not set: enables with default file search

    Returns:
        True if agent instructions should be loaded, False otherwise.
    """
    env_value = os.environ.get(AGENT_INSTRUCTIONS_ENV_VAR, "").lower()
    return env_value not in ("0", "false", "no", "off")
