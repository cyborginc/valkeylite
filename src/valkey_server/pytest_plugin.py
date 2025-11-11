"""Pytest plugin for valkey-server fixtures."""

import pytest

from .server import ValkeyServer


@pytest.fixture
def valkey_server():
    """
    Provide a ValkeyServer instance for a test.

    The server is automatically started and stopped for each test.

    Example:
        def test_my_feature(valkey_server):
            import valkey
            client = valkey.Valkey(**valkey_server.connection_kwargs)
            client.set('key', 'value')
            assert client.get('key') == b'value'
    """
    with ValkeyServer() as server:
        yield server


@pytest.fixture
def valkey_client(valkey_server):
    """
    Provide a connected valkey-py client.

    Requires valkey-py to be installed (pip install valkey-server[pytest]).

    Example:
        def test_my_feature(valkey_client):
            valkey_client.set('key', 'value')
            assert valkey_client.get('key') == b'value'
    """
    try:
        import valkey
    except ImportError:
        pytest.skip("valkey-py not installed (pip install valkey-server[pytest])")

    return valkey_server.client()


@pytest.fixture
def valkey_url(valkey_server):
    """
    Provide the Valkey server connection URL.

    Returns:
        Connection URL string (redis://host:port)

    Example:
        def test_my_feature(valkey_url):
            import valkey
            client = valkey.from_url(valkey_url)
            client.set('key', 'value')
    """
    return valkey_server.connection_url
