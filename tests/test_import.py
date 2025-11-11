"""Test basic imports and module structure."""


def test_import_main_module():
    """Test that the main module can be imported."""
    import valkey_server

    assert valkey_server.__version__ == "8.0.1"


def test_import_server_class():
    """Test that ValkeyServer can be imported."""
    from valkey_server import ValkeyServer

    assert ValkeyServer is not None


def test_import_exceptions():
    """Test that exceptions can be imported."""
    from valkey_server import (
        ValkeyBinaryNotFoundError,
        ValkeyConfigurationError,
        ValkeyServerAlreadyStartedError,
        ValkeyServerError,
        ValkeyServerNotStartedError,
        ValkeyServerStartupError,
        ValkeyServerTimeoutError,
    )

    assert issubclass(ValkeyServerNotStartedError, ValkeyServerError)
    assert issubclass(ValkeyServerAlreadyStartedError, ValkeyServerError)
    assert issubclass(ValkeyServerStartupError, ValkeyServerError)
    assert issubclass(ValkeyServerTimeoutError, ValkeyServerError)
    assert issubclass(ValkeyBinaryNotFoundError, ValkeyServerError)
    assert issubclass(ValkeyConfigurationError, ValkeyServerError)


def test_all_exports():
    """Test that __all__ contains expected exports."""
    from valkey_server import __all__

    expected = {
        "ValkeyServer",
        "ValkeyServerError",
        "ValkeyServerNotStartedError",
        "ValkeyServerAlreadyStartedError",
        "ValkeyServerStartupError",
        "ValkeyServerTimeoutError",
        "ValkeyBinaryNotFoundError",
        "ValkeyConfigurationError",
    }

    assert set(__all__) == expected
