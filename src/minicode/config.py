"""Global configuration management for minicode.

This module handles loading and managing global configuration, including
MCP server configurations from config files. The format is compatible with
Claude Code's MCP configuration format.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default config file locations (in order of precedence)
# Compatible with Claude Code's config file naming
CONFIG_FILE_NAMES = [
    ".mcp.json",  # Project-level config (Claude Code style)
    "mcp.json",
]

# User-level config file path
USER_CONFIG_FILE = ".claude.json"  # Claude Code style

# Environment variable for config file path
CONFIG_ENV_VAR = "MINICODE_CONFIG"


class MCPConfig:
    """Global MCP configuration manager.

    This class handles loading MCP server configurations from:
    1. Environment variable MINICODE_CONFIG pointing to a config file
    2. Config files in the current directory (.mcp.json)
    3. Config files in the user's home directory (~/.claude.json)

    Config file format (JSON, compatible with Claude Code):
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
        cwd = Path.cwd()
        for name in CONFIG_FILE_NAMES:
            path = cwd / name
            if path.exists():
                return path

        # Check home directory for user-level config (Claude Code style)
        home_config = Path.home() / USER_CONFIG_FILE
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
