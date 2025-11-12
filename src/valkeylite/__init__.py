"""
valkeylite: Embedded Valkey server for Python.

Install and run Valkey directly from Python - perfect for testing and development.
Supports Linux (x86_64, aarch64) and macOS (x86_64, arm64).
"""

from .client import Valkey
from .exceptions import (
    ValkeyBinaryNotFoundError,
    ValkeyConfigurationError,
    ValkeyServerAlreadyStartedError,
    ValkeyServerError,
    ValkeyServerNotStartedError,
    ValkeyServerStartupError,
    ValkeyServerTimeoutError,
)
from .server import ValkeyServer

__version__ = "9.0.0"

# Primary exports
__all__ = [
    # Simple API (like redislite.Redis)
    "Valkey",
    # Advanced API (explicit server control)
    "ValkeyServer",
    # Exceptions
    "ValkeyServerError",
    "ValkeyServerNotStartedError",
    "ValkeyServerAlreadyStartedError",
    "ValkeyServerStartupError",
    "ValkeyServerTimeoutError",
    "ValkeyBinaryNotFoundError",
    "ValkeyConfigurationError",
]
