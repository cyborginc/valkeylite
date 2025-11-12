"""Test basic imports and module structure."""


def test_import_main_module():
    """Test that the main module can be imported."""
    import valkeylite

    assert valkeylite.__version__ == "9.0.0"


def test_import_server_class():
    """Test that ValkeyServer can be imported."""
    from valkeylite import ValkeyServer

    assert ValkeyServer is not None


def test_import_client_class():
    """Test that Valkey client wrapper can be imported."""
    from valkeylite import Valkey

    assert Valkey is not None


def test_import_exceptions():
    """Test that exceptions can be imported."""
    from valkeylite import (
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
    from valkeylite import __all__

    expected = {
        "Valkey",
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
