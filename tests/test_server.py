"""Test ValkeyServer behavior."""

import gc
import socket
import warnings
from pathlib import Path

import pytest

import valkeylite.server as server_module
from valkeylite._binary import get_binary_path
from valkeylite.exceptions import ValkeyBinaryNotFoundError, ValkeyServerStartupError

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
def test_server_keeps_responding_with_lots_of_logging(tmp_path):
    """Log output must not fill an unread pipe and hang the server (#46)."""
    server = server_module.ValkeyServer(data_dir=tmp_path, config={"loglevel": "verbose"})
    server.start()
    try:
        # Each connection logs a few lines at verbose; this writes well over 64 KiB.
        for _ in range(500):
            assert _ping(server.host, server.port).startswith(b"+PONG")
        assert server.log_path == tmp_path / "valkey.log"
        assert server.log_path.stat().st_size > 64 * 1024
    finally:
        server.stop()


@requires_binary
def test_custom_logfile_is_resolved_against_data_dir(tmp_path):
    """A relative logfile is written to data_dir, like the server resolves it."""
    with server_module.ValkeyServer(data_dir=tmp_path, config={"logfile": "custom.log"}) as server:
        assert server.log_path == tmp_path / "custom.log"
    assert "Ready to accept connections" in (tmp_path / "custom.log").read_text()


@requires_binary
def test_stop_leaves_no_unclosed_files():
    """stop() must not leak file handles (#45)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ResourceWarning)
        server = server_module.ValkeyServer()
        server.start()
        server.stop()
        gc.collect()

    assert not [w for w in caught if issubclass(w.category, ResourceWarning)]


@requires_binary
def test_startup_failure_reports_log(tmp_path):
    """A startup crash includes what the server logged in the error."""
    server = server_module.ValkeyServer(
        data_dir=tmp_path, config={"loadmodule": str(tmp_path / "missing.so")}
    )
    with pytest.raises(ValkeyServerStartupError, match="missing.so"):
        server.start()


@requires_binary
def test_startup_failure_reports_only_this_runs_log(tmp_path):
    """Earlier runs' log lines in a persistent data_dir are not repeated in the error."""
    (tmp_path / "valkey.log").write_text("line from an earlier run\n")
    server = server_module.ValkeyServer(
        data_dir=tmp_path, config={"loadmodule": str(tmp_path / "missing.so")}
    )
    with pytest.raises(ValkeyServerStartupError) as exc_info:
        server.start()
    assert "earlier run" not in str(exc_info.value)


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
