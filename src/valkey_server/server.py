"""Main ValkeyServer class for managing embedded Valkey server instances."""

import atexit
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

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
        port: Optional[int] = None,
        host: str = "127.0.0.1",
        data_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        persist: bool = False,
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
            **config_overrides: Additional Valkey config options as keyword arguments.

        Raises:
            ValkeyBinaryNotFoundError: If Valkey binary cannot be found.
            ValkeyConfigurationError: If configuration is invalid.
            OSError: If port is already in use.
        """
        self.host = host
        self._port: Optional[int] = None  # Will be set in start()
        self._desired_port = port  # User-requested port
        self.persist = persist

        # Merge config with overrides
        self._config = config.copy() if config else {}
        self._config.update(config_overrides)

        # Validate configuration
        validate_config(self._config)

        # Setup directories
        self._temp_data_dir: Optional[Path] = None
        if data_dir is None:
            self._temp_data_dir = Path(tempfile.mkdtemp(prefix="valkey-"))
            self.data_dir = self._temp_data_dir
        else:
            self.data_dir = Path(data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)

        self._temp_config_file: Optional[Path] = None
        self._process: Optional[subprocess.Popen] = None
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
        return f"redis://{self.host}:{self.port}"

    @property
    def connection_kwargs(self) -> Dict[str, Any]:
        """Get connection parameters as a dictionary for valkey-py client."""
        return {
            "host": self.host,
            "port": self.port,
        }

    def client(self, **kwargs: Any) -> Any:
        """
        Create a valkey-py client connected to this server.

        Requires: pip install valkey-server[client]

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
                "Install with: pip install valkey-server[client]"
            ) from e

        return valkey.Valkey(host=self.host, port=self.port, **kwargs)

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

        # Assign port
        self._port = get_port_or_find_free(self._desired_port, self.host)

        # Generate config file
        self._temp_config_file = self.data_dir / "valkey.conf"
        generate_config_file(
            self._temp_config_file,
            self._port,
            self.data_dir,
            self._config,
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
            True if server is running and accepting connections
        """
        if self._process is None or self._port is None:
            return False

        # Check if process is alive
        if self._process.poll() is not None:
            return False

        # Check if we can connect
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1.0)
                sock.connect((self.host, self._port))
            return True
        except (socket.error, OSError):
            return False

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
                stderr = self._process.stderr.read().decode() if self._process.stderr else ""
                raise ValkeyServerStartupError(
                    f"Valkey server process died during startup. stderr: {stderr}"
                )

            # Try to connect
            if self.is_running():
                return

            time.sleep(0.1)

        raise ValkeyServerTimeoutError(
            f"Server did not become ready within {timeout} seconds"
        )

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
            return f"<ValkeyServer running at {self.host}:{self._port}>"
        return "<ValkeyServer not running>"
