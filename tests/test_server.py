"""Test ValkeyServer behavior."""

from pathlib import Path

import valkeylite.server as server_module


def test_unix_socket_connection_info(monkeypatch, tmp_path):
    """Test Unix socket connection metadata."""
    socket_path = tmp_path / "valkey.sock"
    monkeypatch.setattr(server_module, "get_binary_path", lambda: Path("/tmp/valkey-server"))

    server = server_module.ValkeyServer(
        port=0,
        data_dir=tmp_path,
        unix_socket_path=socket_path,
    )

    assert server.connection_url == f"valkey+unix://{socket_path}"
    assert server.connection_kwargs == {"unix_socket_path": str(socket_path)}


def test_tcp_connection_info_unchanged(monkeypatch, tmp_path):
    """Test TCP connection metadata."""
    monkeypatch.setattr(server_module, "get_binary_path", lambda: Path("/tmp/valkey-server"))

    server = server_module.ValkeyServer(port=6380, data_dir=tmp_path)
    server._port = 6380

    assert server.connection_url == "redis://127.0.0.1:6380"
    assert server.connection_kwargs == {"host": "127.0.0.1", "port": 6380}
