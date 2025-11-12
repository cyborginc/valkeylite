"""Valkey client wrapper with embedded server (redislite-compatible API)."""

import atexit
from pathlib import Path
from typing import Any

import valkey

from .server import ValkeyServer


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
            **kwargs: Additional arguments passed to valkey.Valkey client

        Example:
            # Temporary (in-memory, no persistence)
            r = Valkey()

            # Persistent (data saved to file)
            r = Valkey('/tmp/mydata.db')

            # Custom port
            r = Valkey(port=6380)
        """
        # Start embedded server
        self._server = ValkeyServer(
            port=port,
            host=host,
            data_dir=Path(dbfilename) if dbfilename else None,
            persist=bool(dbfilename),
        )
        self._server.start()

        # Initialize parent valkey.Valkey client
        super().__init__(
            host=self._server.host,
            port=self._server.port,
            **kwargs,
        )

        # Register cleanup handler
        atexit.register(self._cleanup)

    @property
    def server(self) -> ValkeyServer:
        """Get the underlying ValkeyServer instance."""
        return self._server

    def close(self) -> None:
        """Close client connection and stop embedded server."""
        try:
            super().close()
        finally:
            if self._server:
                self._server.stop()
                self._server = None

    def _cleanup(self) -> None:
        """Cleanup handler called on exit."""
        if self._server:
            try:
                self._server.terminate()
            except Exception:
                pass

    def __enter__(self) -> "Valkey":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - close client and stop server."""
        self.close()

    def __del__(self) -> None:
        """Destructor - ensure cleanup."""
        self._cleanup()
