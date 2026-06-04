"""Test Valkey client wrapper behavior."""

import pytest

import valkeylite.client as client_module
from valkeylite._binary import get_binary_path
from valkeylite.client import Valkey
from valkeylite.exceptions import ValkeyBinaryNotFoundError

try:
    get_binary_path()
    _HAS_BINARY = True
except ValkeyBinaryNotFoundError:
    _HAS_BINARY = False

requires_binary = pytest.mark.skipif(
    not _HAS_BINARY, reason="valkey-server binary not built for this platform"
)


class FakeServer:
    """Minimal ValkeyServer stand-in for client lifecycle tests."""

    instances = []

    def __init__(
        self,
        port=None,
        host="127.0.0.1",
        data_dir=None,
        persist=False,
        unix_socket_path=None,
        unix_socket_perm="700",
    ):
        self.port = port
        self.host = host
        self.data_dir = data_dir
        self.persist = persist
        self.unix_socket_path = unix_socket_path
        self.unix_socket_perm = unix_socket_perm
        self.started = False
        self.stopped = False
        self.terminated = False
        FakeServer.instances.append(self)

    @property
    def connection_kwargs(self):
        if self.unix_socket_path is not None:
            return {"unix_socket_path": str(self.unix_socket_path)}
        return {"host": self.host, "port": self.port}

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def terminate(self):
        self.terminated = True

    def is_running(self):
        return self.started and not self.stopped and not self.terminated


def test_persistent_clients_share_socket_server(monkeypatch, tmp_path):
    """Test persistent clients reuse a Unix socket server and do not stop it on close."""
    monkeypatch.setattr(client_module, "ValkeyServer", FakeServer)
    client_module._SHARED_SERVERS.clear()
    FakeServer.instances.clear()

    first = Valkey(tmp_path)
    second = Valkey(tmp_path)
    server = first.server

    assert first.server is second.server
    # TCP stays enabled (port auto-assigned, not forced to 0) alongside the
    # Unix socket; sharing alone prevents the port churn/exhaustion.
    assert server.port is None
    assert server.unix_socket_path == tmp_path.resolve() / "valkey.sock"

    first.close()
    second.close()

    assert not server.stopped
    assert len(FakeServer.instances) == 1


def test_temporary_client_stops_owned_server(monkeypatch):
    """Test non-persistent clients still own their server lifecycle."""
    monkeypatch.setattr(client_module, "ValkeyServer", FakeServer)
    client_module._SHARED_SERVERS.clear()
    FakeServer.instances.clear()

    client = Valkey(port=6380)
    server = client.server
    client.close()

    assert server.stopped


@requires_binary
def test_persistent_client_real_server_socket_and_sharing(tmp_path):
    """End-to-end: a persistent client starts a real server with a stable Unix
    socket + TCP, reuses one server per path, and shares data across clients."""
    import valkey as valkey_py

    db = tmp_path / "mydb"
    client_module._SHARED_SERVERS.clear()

    first = Valkey(db)
    server = first.server
    try:
        # Unix socket is enabled at the default path and exposed via config_get.
        expected_socket = db.resolve() / "valkey.sock"
        assert server.unix_socket_path == expected_socket
        assert expected_socket.exists()
        assert first.config_get()["unixsocket"] == str(expected_socket)

        # TCP stays enabled alongside the socket (not disabled with port 0).
        assert server.port > 0
        tcp = valkey_py.Valkey(host="127.0.0.1", port=server.port)
        try:
            assert tcp.ping() is True
        finally:
            tcp.close()

        first.set("shared-key", "shared-value")

        # A second client for the same path reuses the same server and data.
        second = Valkey(db)
        try:
            assert second.server is server
            assert second.server.port == server.port
            assert second.get("shared-key") == b"shared-value"
        finally:
            second.close()

        # Closing a shared client must not stop the server others may rely on.
        first.close()
        assert server.is_running()
    finally:
        client_module._SHARED_SERVERS.clear()
        if server.is_running():
            server.stop()


@requires_binary
def test_relative_dbfilename_starts(monkeypatch):
    """A relative dbfilename must start (regression: cwd=data_dir doubled the
    relative path into 'name.db/name.db/valkey.conf' and the server died).

    Uses a short cwd so the default <data_dir>/valkey.sock stays under the
    ~104-char Unix socket path limit, which is unrelated to this regression.
    """
    import shutil
    import tempfile

    short_cwd = tempfile.mkdtemp(prefix="vlt", dir="/tmp")
    monkeypatch.chdir(short_cwd)
    client_module._SHARED_SERVERS.clear()

    r = Valkey("somename.db")
    server = r.server
    try:
        assert server.data_dir.is_absolute()
        r.set("k", "v")
        assert r.get("k") == b"v"
        r.close()
    finally:
        client_module._SHARED_SERVERS.clear()
        if server.is_running():
            server.stop()
        shutil.rmtree(short_cwd, ignore_errors=True)
