"""Custom exceptions for valkey-server."""


class ValkeyServerError(Exception):
    """Base exception for all valkey-server errors."""

    pass


class ValkeyServerNotStartedError(ValkeyServerError):
    """Raised when attempting to operate on a server that hasn't been started."""

    pass


class ValkeyServerAlreadyStartedError(ValkeyServerError):
    """Raised when attempting to start a server that's already running."""

    pass


class ValkeyServerStartupError(ValkeyServerError):
    """Raised when the Valkey server fails to start."""

    pass


class ValkeyServerTimeoutError(ValkeyServerError):
    """Raised when an operation times out."""

    pass


class ValkeyBinaryNotFoundError(ValkeyServerError):
    """Raised when the Valkey binary cannot be found for the current platform."""

    pass


class ValkeyConfigurationError(ValkeyServerError):
    """Raised when there's an error in the configuration."""

    pass
