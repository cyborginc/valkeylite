"""Pytest plugin for valkeylite fixtures."""

import importlib.util

import pytest

from .server import ValkeyServer


@pytest.fixture
def valkeylite():
    """
    Provide a ValkeyServer instance for a test.

    The server is automatically started and stopped for each test.

    Example:
        def test_my_feature(valkeylite):
            import valkey
            client = valkey.Valkey(**valkeylite.connection_kwargs)
            client.set('key', 'value')
            assert client.get('key') == b'value'
    """
    with ValkeyServer() as server:
        yield server


@pytest.fixture
def valkey_client(valkeylite):
    """
    Provide a connected valkey-py client.

    Requires valkey-py to be installed (pip install valkeylite[test]).

    Example:
        def test_my_feature(valkey_client):
            valkey_client.set('key', 'value')
            assert valkey_client.get('key') == b'value'
    """
    if importlib.util.find_spec("valkey") is None:
        pytest.skip("valkey-py not installed (pip install valkeylite[test])")

    return valkeylite.client()


@pytest.fixture
def valkey_url(valkeylite):
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
    return valkeylite.connection_url
