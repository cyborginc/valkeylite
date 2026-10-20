"""Test ValkeyServer behavior."""

import socket
from pathlib import Path

import pytest

import valkeylite.server as server_module
from valkeylite._binary import get_binary_path
from valkeylite.exceptions import ValkeyBinaryNotFoundError

try:
    get_binary_path()
    _HAS_BINARY = True
except ValkeyBinaryNotFoundError:
    _HAS_BINARY = False

requires_binary = pytest.mark.skipif(
    not _HAS_BINARY, reason="valkey-server binary not built for this platform"
)


def _ping(host: str, port: int) -> bytes:
    with socket.create_connection((host, port), timeout=3) as sock:
        sock.sendall(b"*1\r\n$4\r\nPING\r\n")
        return sock.recv(64)


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


@requires_binary
def test_restart_on_same_port_with_connected_client():
    """Restarting on a fixed port works while the old connections linger (#44)."""
    server = server_module.ValkeyServer()
    server.start()
    port = server.port

    # A client that is still connected when the server goes down
    client = socket.create_connection(("127.0.0.1", port))
    client.sendall(b"*1\r\n$4\r\nPING\r\n")
    client.recv(64)
    server.stop()
    client.close()

    server = server_module.ValkeyServer(port=port)
    server.start()
    try:
        assert _ping(server.host, port).startswith(b"+PONG")
    finally:
        server.stop()
