"""Tests for global configuration management."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from minicode.config import (
    MCPConfig,
    add_global_mcp_server,
    get_global_mcp_servers,
)


@pytest.fixture(autouse=True)
def reset_config():
    """Reset MCPConfig singleton before each test."""
    MCPConfig.reset()
    yield
    MCPConfig.reset()


class TestMCPConfig:
    """Tests for MCPConfig class."""

    def test_singleton_pattern(self):
        """Test that MCPConfig is a singleton."""
        config1 = MCPConfig()
        config2 = MCPConfig()
        assert config1 is config2

    def test_reset_clears_singleton(self):
        """Test that reset clears the singleton instance."""
        config1 = MCPConfig()
        MCPConfig.reset()
        config2 = MCPConfig()
        assert config1 is not config2

    def test_get_servers_returns_empty_list_by_default(self):
        """Test that get_servers returns empty list when no config exists."""
        config = MCPConfig()
        servers = config.get_servers()
        assert servers == []

    def test_add_server_programmatically(self):
        """Test adding a server configuration programmatically."""
        config = MCPConfig()
        config.add_server({
            "name": "test-server",
            "command": ["echo", "test"],
        })

        servers = config.get_servers()
        assert len(servers) == 1
        assert servers[0]["name"] == "test-server"

    def test_clear_servers(self):
        """Test clearing all server configurations."""
        config = MCPConfig()
        config.add_server({"name": "server1", "command": ["echo", "1"]})
        config.add_server({"name": "server2", "command": ["echo", "2"]})

        assert len(config.get_servers()) == 2

        config.clear_servers()
        assert len(config.get_servers()) == 0

    def test_get_servers_returns_copy(self):
        """Test that get_servers returns a copy, not the original list."""
        config = MCPConfig()
        config.add_server({"name": "test", "command": ["echo"]})

        servers1 = config.get_servers()
        servers2 = config.get_servers()

        assert servers1 is not servers2
        assert servers1 == servers2


class TestMCPConfigFileLoading:
    """Tests for config file loading (Claude Code format)."""

    def test_load_from_mcp_json_file(self):
        """Test loading config from .mcp.json file (Claude Code format)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".mcp.json"
            config_data = {
                "mcpServers": {
                    "memory": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-memory"],
                    },
                    "remote": {
                        "type": "http",
                        "url": "http://localhost:8080/mcp",
                    },
                }
            }
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = MCPConfig()
                config.load()

                servers = config.get_servers()
                assert len(servers) == 2

                # Find memory server
                memory_server = next(s for s in servers if s["name"] == "memory")
                assert memory_server["command"] == ["npx", "-y", "@modelcontextprotocol/server-memory"]

                # Find remote server
                remote_server = next(s for s in servers if s["name"] == "remote")
                assert remote_server["url"] == "http://localhost:8080/mcp"
            finally:
                os.chdir(original_cwd)

    def test_load_stdio_server_with_env(self):
        """Test loading stdio server with environment variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".mcp.json"
            config_data = {
                "mcpServers": {
                    "test-server": {
                        "type": "stdio",
                        "command": "python",
                        "args": ["-m", "my_server"],
                        "env": {"API_KEY": "secret123"},
                    }
                }
            }
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = MCPConfig()
                config.load()

                servers = config.get_servers()
                assert len(servers) == 1
                assert servers[0]["name"] == "test-server"
                assert servers[0]["command"] == ["python", "-m", "my_server"]
                assert servers[0]["env"] == {"API_KEY": "secret123"}
            finally:
                os.chdir(original_cwd)

    def test_load_http_server_with_headers(self):
        """Test loading HTTP server with custom headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".mcp.json"
            config_data = {
                "mcpServers": {
                    "api-server": {
                        "type": "http",
                        "url": "https://api.example.com/mcp",
                        "headers": {"Authorization": "Bearer token123"},
                    }
                }
            }
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = MCPConfig()
                config.load()

                servers = config.get_servers()
                assert len(servers) == 1
                assert servers[0]["name"] == "api-server"
                assert servers[0]["url"] == "https://api.example.com/mcp"
                assert servers[0]["headers"] == {"Authorization": "Bearer token123"}
            finally:
                os.chdir(original_cwd)

    def test_load_from_env_variable(self):
        """Test loading config from path specified in environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "custom-config.json"
            config_data = {
                "mcpServers": {
                    "env-server": {
                        "type": "stdio",
                        "command": "echo",
                        "args": ["env"],
                    }
                }
            }
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            with patch.dict(os.environ, {"MINICODE_CONFIG": str(config_path)}):
                config = MCPConfig()
                config.load()

                servers = config.get_servers()
                assert len(servers) == 1
                assert servers[0]["name"] == "env-server"
                assert servers[0]["command"] == ["echo", "env"]

    def test_load_handles_invalid_json(self):
        """Test that invalid JSON files are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".mcp.json"
            with open(config_path, "w") as f:
                f.write("not valid json {{{")

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = MCPConfig()
                config.load()

                servers = config.get_servers()
                assert servers == []
            finally:
                os.chdir(original_cwd)

    def test_load_handles_missing_mcp_servers_key(self):
        """Test that config without mcpServers key returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".mcp.json"
            config_data = {"other_setting": "value"}
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = MCPConfig()
                config.load()

                servers = config.get_servers()
                assert servers == []
            finally:
                os.chdir(original_cwd)

    def test_force_reload(self):
        """Test that force=True reloads the config."""
        config = MCPConfig()
        config.add_server({"name": "added", "command": ["echo"]})
        assert len(config.get_servers()) == 1

        config.load(force=True)
        assert len(config.get_servers()) == 0

    def test_default_type_is_stdio(self):
        """Test that servers without explicit type default to stdio."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".mcp.json"
            config_data = {
                "mcpServers": {
                    "default-server": {
                        "command": "my-command",
                        "args": ["--flag"],
                    }
                }
            }
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = MCPConfig()
                config.load()

                servers = config.get_servers()
                assert len(servers) == 1
                assert servers[0]["command"] == ["my-command", "--flag"]
            finally:
                os.chdir(original_cwd)


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_global_mcp_servers(self):
        """Test get_global_mcp_servers function."""
        servers = get_global_mcp_servers()
        assert servers == []

    def test_add_global_mcp_server(self):
        """Test add_global_mcp_server function with command and args."""
        add_global_mcp_server(
            name="test-server",
            command="echo",
            args=["test"],
            env={"KEY": "value"},
        )

        servers = get_global_mcp_servers()
        assert len(servers) == 1
        assert servers[0]["name"] == "test-server"
        assert servers[0]["command"] == ["echo", "test"]
        assert servers[0]["env"] == {"KEY": "value"}

    def test_add_global_mcp_server_http(self):
        """Test add_global_mcp_server with HTTP transport."""
        add_global_mcp_server(
            name="http-server",
            url="http://localhost:8080/mcp",
            headers={"Authorization": "Bearer token"},
        )

        servers = get_global_mcp_servers()
        assert len(servers) == 1
        assert servers[0]["name"] == "http-server"
        assert servers[0]["url"] == "http://localhost:8080/mcp"
        assert servers[0]["headers"] == {"Authorization": "Bearer token"}

    def test_add_global_mcp_server_no_args(self):
        """Test add_global_mcp_server with command only (no args)."""
        add_global_mcp_server(
            name="simple-server",
            command="my-server",
        )

        servers = get_global_mcp_servers()
        assert len(servers) == 1
        assert servers[0]["command"] == ["my-server"]


class TestAgentGlobalMCPIntegration:
    """Tests for Agent integration with global MCP config."""

    def test_agent_loads_global_config_by_default(self):
        """Test that Agent loads global MCP config by default."""
        add_global_mcp_server(name="global-server", command="echo", args=["global"])

        from minicode import Agent
        from minicode.llm.base import BaseLLM

        mock_llm = MagicMock(spec=BaseLLM)
        agent = Agent(name="test", llm=mock_llm)

        assert agent._mcp_servers_config is not None
        assert len(agent._mcp_servers_config) == 1
        assert agent._mcp_servers_config[0]["name"] == "global-server"

    def test_agent_can_disable_global_config(self):
        """Test that Agent can disable global MCP config."""
        add_global_mcp_server(name="global-server", command="echo", args=["global"])

        from minicode import Agent
        from minicode.llm.base import BaseLLM

        mock_llm = MagicMock(spec=BaseLLM)
        agent = Agent(name="test", llm=mock_llm, use_global_mcp=False)

        assert agent._mcp_servers_config is None

    def test_agent_combines_global_and_explicit_config(self):
        """Test that Agent combines global and explicit MCP configs."""
        add_global_mcp_server(name="global-server", command="echo", args=["global"])

        from minicode import Agent
        from minicode.llm.base import BaseLLM

        mock_llm = MagicMock(spec=BaseLLM)
        agent = Agent(
            name="test",
            llm=mock_llm,
            mcp_servers=[{"name": "explicit-server", "command": ["echo", "explicit"]}],
        )

        assert agent._mcp_servers_config is not None
        assert len(agent._mcp_servers_config) == 2

        names = {c["name"] for c in agent._mcp_servers_config}
        assert "global-server" in names
        assert "explicit-server" in names

    def test_agent_explicit_config_overrides_global(self):
        """Test that explicit config overrides global config with same name."""
        add_global_mcp_server(name="shared-name", command="echo", args=["global"])

        from minicode import Agent
        from minicode.llm.base import BaseLLM

        mock_llm = MagicMock(spec=BaseLLM)
        agent = Agent(
            name="test",
            llm=mock_llm,
            mcp_servers=[{"name": "shared-name", "command": ["echo", "explicit"]}],
        )

        assert agent._mcp_servers_config is not None
        assert len(agent._mcp_servers_config) == 1
        assert agent._mcp_servers_config[0]["name"] == "shared-name"
        assert agent._mcp_servers_config[0]["command"] == ["echo", "explicit"]
