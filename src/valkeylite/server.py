"""Main ValkeyServer class for managing embedded Valkey server instances."""

import atexit
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from ._binary import get_binary_path
from .config import generate_config_file, validate_config
from .exceptions import (
    ValkeyServerAlreadyStartedError,
    ValkeyServerNotStartedError,
    ValkeyServerStartupError,
    ValkeyServerTimeoutError,
)
from .port_finder import get_port_or_find_free


class ValkeyServer:
    """
    Embedded Valkey server for testing and development.

    Example:
        >>> with ValkeyServer() as server:
        ...     client = server.client()
        ...     client.set('key', 'value')
        ...     assert client.get('key') == b'value'
    """

    def __init__(
        self,
        port: int | None = None,
        host: str = "127.0.0.1",
        data_dir: Path | None = None,
        config: dict[str, Any] | None = None,
        persist: bool = False,
        unix_socket_path: str | Path | None = None,
        unix_socket_perm: str | int = "700",
        **config_overrides: Any,
    ) -> None:
        """
        Initialize a Valkey server instance.

        Args:
            port: Port to bind to. If None, automatically finds a free port.
            host: Host address to bind to (default: 127.0.0.1).
            data_dir: Directory for Valkey data files. If None, uses temp directory.
            config: Dictionary of Valkey configuration options.
            persist: If True, keep data_dir after shutdown. Default: False.
            unix_socket_path: Optional Unix socket path for local clients.
            unix_socket_perm: Unix socket permissions. Default: 700.
            **config_overrides: Additional Valkey config options as keyword arguments.

        Raises:
            ValkeyBinaryNotFoundError: If Valkey binary cannot be found.
            ValkeyConfigurationError: If configuration is invalid.
            OSError: If port is already in use.
        """
        self.host = host
        self._port: int | None = None  # Will be set in start()
        self._desired_port = port  # User-requested port
        self.persist = persist
        self.unix_socket_path = Path(unix_socket_path) if unix_socket_path else None
        self.unix_socket_perm = unix_socket_perm

        # Merge config with overrides
        self._config = config.copy() if config else {}
        self._config.update(config_overrides)

        # Validate configuration
        validate_config(self._config)

        # Setup directories
        self._temp_data_dir: Path | None = None
        if data_dir is None:
            self._temp_data_dir = Path(tempfile.mkdtemp(prefix="valkey-"))
            self.data_dir = self._temp_data_dir
        else:
            # Resolve to an absolute path: start() runs the server with
            # cwd=data_dir, so a relative dir would be re-resolved against
            # itself (e.g. "somename.db/somename.db/valkey.conf") and fail.
            self.data_dir = Path(data_dir).resolve()
            self.data_dir.mkdir(parents=True, exist_ok=True)

        self._temp_config_file: Path | None = None
        self._process: subprocess.Popen | None = None
        self._binary_path = get_binary_path()

        # Register cleanup handler
        atexit.register(self._cleanup)

    @property
    def port(self) -> int:
        """Get the port the server is bound to."""
        if self._port is None:
            raise ValkeyServerNotStartedError(
                "Server has not been started yet. Call start() first."
            )
        return self._port

    @property
    def connection_url(self) -> str:
        """Get Redis-protocol connection URL."""
        if self.unix_socket_path is not None:
            return f"valkey+unix://{self.unix_socket_path}"
        return f"redis://{self.host}:{self.port}"

    @property
    def connection_kwargs(self) -> dict[str, Any]:
        """Get connection parameters as a dictionary for valkey-py client."""
        if self.unix_socket_path is not None:
            return {"unix_socket_path": str(self.unix_socket_path)}
        return {
            "host": self.host,
            "port": self.port,
        }

    def client(self, **kwargs: Any) -> Any:
        """
        Create a valkey-py client connected to this server.

        Requires: pip install valkeylite[client]

        Args:
            **kwargs: Additional arguments passed to valkey.Valkey()

        Returns:
            valkey.Valkey client instance

        Raises:
            ImportError: If valkey-py is not installed
            ValkeyServerNotStartedError: If server is not running
        """
        if not self.is_running():
            raise ValkeyServerNotStartedError(
                "Server must be started before creating a client. "
                "Use 'with ValkeyServer() as server:' or call server.start()"
            )

        try:
            import valkey
        except ImportError as e:
            raise ImportError(
                "valkey-py is required for the client() method. "
                "Install with: pip install valkeylite[client]"
            ) from e

        return valkey.Valkey(**self.connection_kwargs, **kwargs)

    def start(self, timeout: float = 10.0) -> None:
        """
        Start the Valkey server and wait until it's ready.

        Args:
            timeout: Maximum time to wait for server to start (seconds)

        Raises:
            ValkeyServerAlreadyStartedError: If server is already running
            ValkeyServerStartupError: If server fails to start
            ValkeyServerTimeoutError: If server doesn't start within timeout
        """
        if self._process is not None:
            raise ValkeyServerAlreadyStartedError("Server is already running")

        # Assign port. Port 0 disables TCP when using a Unix socket.
        self._port = (
            0 if self._desired_port == 0 else get_port_or_find_free(self._desired_port, self.host)
        )

        if self.unix_socket_path is not None:
            self._prepare_unix_socket()

        # Generate config file
        self._temp_config_file = self.data_dir / "valkey.conf"
        generate_config_file(
            self._temp_config_file,
            self._port,
            self.data_dir,
            self._config,
            self.unix_socket_path,
            self.unix_socket_perm,
        )

        # Start Valkey process
        try:
            self._process = subprocess.Popen(
                [str(self._binary_path), str(self._temp_config_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.data_dir),
            )
        except Exception as e:
            raise ValkeyServerStartupError(f"Failed to start Valkey server: {e}") from e

        # Wait for server to be ready
        try:
            self.wait_until_ready(timeout)
        except Exception as e:
            # Kill the process if startup failed
            self.terminate()
            raise ValkeyServerStartupError(f"Server failed to start: {e}") from e

    def stop(self, timeout: float = 5.0) -> None:
        """
        Gracefully stop the Valkey server.

        Args:
            timeout: Maximum time to wait for graceful shutdown (seconds)

        Raises:
            ValkeyServerNotStartedError: If server is not running
        """
        if self._process is None:
            raise ValkeyServerNotStartedError("Server is not running")

        # Send SIGTERM for graceful shutdown
        try:
            self._process.terminate()
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Force kill if graceful shutdown times out
            self._process.kill()
            self._process.wait(timeout=1.0)
        finally:
            self._process = None
            self._port = None

    def terminate(self) -> None:
        """Forcefully terminate the Valkey server (SIGKILL)."""
        if self._process is not None:
            self._process.kill()
            try:
                self._process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass
            finally:
                self._process = None
                self._port = None

    def is_running(self) -> bool:
        """
        Check if the server is running and responding.

        Returns:
            True if the server process is alive and replies +PONG to PING.
            A bare TCP connect is not enough: a server that has opened its
            listening socket but then aborts during startup (e.g. a failed
            module load) accepts the connection and resets it on the first
            command. Sending a real PING catches that case.
        """
        if self._process is None or self._port is None:
            return False

        # Check if process is alive
        if self._process.poll() is not None:
            return False

        # Connect and exchange a real RESP PING/PONG. Use a raw socket so this
        # does not depend on the optional valkey client library.
        try:
            self._check_connection()
            return True
        except OSError:
            return False

    def _prepare_unix_socket(self) -> None:
        """Create the socket directory and remove stale socket files."""
        if self.unix_socket_path is None:
            return

        self.unix_socket_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.unix_socket_path.exists():
            return

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(1.0)
                sock.connect(str(self.unix_socket_path))
        except OSError:
            self.unix_socket_path.unlink()
            return

        raise ValkeyServerStartupError(f"Unix socket already in use: {self.unix_socket_path}")

    def _check_connection(self) -> None:
        """Connect and verify the server replies +PONG to a RESP PING.

        Raises OSError if the connection fails or the server does not reply
        with +PONG. A bare connect is not enough: a server that has opened its
        listening socket but then aborts during startup (e.g. a failed module
        load) accepts the connection and resets it on the first command.
        """
        if self.unix_socket_path is not None:
            family: int = socket.AF_UNIX
            address: Any = str(self.unix_socket_path)
        else:
            family = socket.AF_INET
            address = (self.host, self.port)

        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            sock.connect(address)
            sock.sendall(b"*1\r\n$4\r\nPING\r\n")
            response = sock.recv(64)

        if not response.startswith(b"+PONG"):
            raise OSError(f"Server did not reply +PONG to PING: {response!r}")

    def wait_until_ready(self, timeout: float = 10.0) -> None:
        """
        Wait until the server is ready to accept connections.

        Args:
            timeout: Maximum time to wait (seconds)

        Raises:
            ValkeyServerTimeoutError: If server doesn't become ready within timeout
            ValkeyServerStartupError: If server process dies during startup
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if process died
            if self._process and self._process.poll() is not None:
                # Valkey logs to stdout (logfile ""), so include both streams —
                # startup crashes (e.g. a failed module load) print to stdout,
                # not stderr.
                stdout = self._process.stdout.read().decode() if self._process.stdout else ""
                stderr = self._process.stderr.read().decode() if self._process.stderr else ""
                raise ValkeyServerStartupError(
                    f"Valkey server process died during startup "
                    f"(exit code {self._process.returncode}).\n"
                    f"stdout:\n{stdout}\nstderr:\n{stderr}"
                )

            # Try to connect
            if self.is_running():
                return

            time.sleep(0.1)

        raise ValkeyServerTimeoutError(f"Server did not become ready within {timeout} seconds")

    def _cleanup(self) -> None:
        """Clean up resources (called automatically at exit)."""
        # Stop server if running
        if self._process is not None:
            try:
                self.terminate()
            except Exception:
                pass

        # Remove temp config file
        if self._temp_config_file and self._temp_config_file.exists():
            try:
                self._temp_config_file.unlink()
            except Exception:
                pass

        # Remove temp data directory if not persisting
        if not self.persist and self._temp_data_dir and self._temp_data_dir.exists():
            try:
                shutil.rmtree(self._temp_data_dir)
            except Exception:
                pass

    def __enter__(self) -> "ValkeyServer":
        """Context manager entry - starts the server."""
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - stops the server."""
        self.stop()

    def __del__(self) -> None:
        """Destructor - ensure cleanup happens."""
        self._cleanup()

    def __repr__(self) -> str:
        """String representation of the server."""
        if self.is_running():
            if self.unix_socket_path is not None:
                return f"<ValkeyServer running at {self.unix_socket_path}>"
            return f"<ValkeyServer running at {self.host}:{self._port}>"
        return "<ValkeyServer not running>"
