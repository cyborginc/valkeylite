"""Valkey client wrapper with embedded server (redislite-compatible API)."""

import atexit
import threading
from pathlib import Path
from typing import Any

import valkey

from .server import ValkeyServer

# Embedded servers shared within this process, keyed by resolved data_dir.
# Reusing one server per persistent directory avoids port churn/exhaustion and,
# critically, prevents two processes-of-one-interpreter from writing the same
# RDB. This is per-interpreter only: separate OS processes (e.g. gunicorn
# workers) each get their own server — for multi-worker deployments point
# flask_limiter at an external valkey/redis instead.
_SHARED_SERVERS: dict[Path, ValkeyServer] = {}
_SHARED_SERVERS_LOCK = threading.Lock()


class Valkey(valkey.Valkey):
    """
    Valkey client with embedded server management.

    This class provides a redislite-compatible API where the server is
    automatically started and managed behind the scenes.

    Example:
        >>> r = Valkey()
        >>> r.set('key', 'value')
        >>> r.get('key')
        b'value'
        >>> r.close()

    Or with context manager:
        >>> with Valkey() as r:
        ...     r.set('key', 'value')
        ...     assert r.get('key') == b'value'

    For more control, use ValkeyServer directly.
    """

    def __init__(
        self,
        dbfilename: str | Path | None = None,
        host: str = "127.0.0.1",
        port: int | None = None,
        unix_socket_path: str | Path | None = None,
        unix_socket_perm: str | int = "700",
        **kwargs: Any,
    ) -> None:
        """
        Initialize Valkey client with embedded server.

        Args:
            dbfilename: Optional path for persistent data directory.
                       If None, uses temporary directory (data not persisted).
                       If provided, data is persisted to this location.
            host: Host to bind server to (default: 127.0.0.1)
            port: Port to bind server to (default: auto-assign)
            unix_socket_path: Optional Unix socket path.
                              Defaults to <dbfilename>/valkey.sock when dbfilename is set.
            unix_socket_perm: Unix socket permissions. Default: 700.
            **kwargs: Additional arguments passed to valkey.Valkey client

        Example:
            # Temporary (in-memory, no persistence)
            r = Valkey()

            # Persistent (data saved to file)
            r = Valkey('/tmp/mydata.db')

            # Custom port
            r = Valkey(port=6380)
        """
        data_dir = Path(dbfilename) if dbfilename else None
        self._shared_server_key: Path | None = None
        self._server = self._get_server(data_dir, host, port, unix_socket_path, unix_socket_perm)

        # Initialize parent valkey.Valkey client
        super().__init__(**self._server.connection_kwargs, **kwargs)

        # Register cleanup handler
        atexit.register(self._cleanup)

    @property
    def server(self) -> ValkeyServer:
        """Get the underlying ValkeyServer instance."""
        return self._server

    def close(self) -> None:
        """Close the client connection and any self-owned embedded server."""
        try:
            super().close()
        finally:
            if self._server:
                if self._shared_server_key is None:
                    self._server.stop()
                self._server = None

    def _cleanup(self) -> None:
        """Cleanup handler called on exit."""
        server = getattr(self, "_server", None)
        if server:
            try:
                if getattr(self, "_shared_server_key", None) is None:
                    server.terminate()
            except Exception:
                pass

    def _get_server(
        self,
        data_dir: Path | None,
        host: str,
        port: int | None,
        unix_socket_path: str | Path | None,
        unix_socket_perm: str | int,
    ) -> ValkeyServer:
        if data_dir is not None and port is None:
            key = data_dir.resolve()
            # Hold the lock across the check-and-start so concurrent threads
            # can't both spawn a server on the same data_dir (which would race
            # on the socket and risk dual-writer RDB corruption).
            with _SHARED_SERVERS_LOCK:
                server = _SHARED_SERVERS.get(key)
                if server is None or not server.is_running():
                    socket_path = (
                        Path(unix_socket_path) if unix_socket_path else key / "valkey.sock"
                    )
                    # Keep TCP enabled (auto-assigned port) alongside the unix
                    # socket. Sharing already prevents port churn/exhaustion, so
                    # there's no reason to disable TCP — and doing so would break
                    # callers that connect over host/port or read config_get()['port'].
                    server = ValkeyServer(
                        port=None,
                        host=host,
                        data_dir=data_dir,
                        persist=True,
                        unix_socket_path=socket_path,
                        unix_socket_perm=unix_socket_perm,
                    )
                    server.start()
                    _SHARED_SERVERS[key] = server
                self._shared_server_key = key
                return server

        server = ValkeyServer(
            port=port,
            host=host,
            data_dir=data_dir,
            persist=bool(data_dir),
            unix_socket_path=Path(unix_socket_path) if unix_socket_path else None,
            unix_socket_perm=unix_socket_perm,
        )
        server.start()
        return server

    def __enter__(self) -> "Valkey":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - close client and stop server."""
        self.close()

    def __del__(self) -> None:
        """Destructor - ensure cleanup."""
        self._cleanup()
