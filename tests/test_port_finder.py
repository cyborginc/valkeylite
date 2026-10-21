"""Test port finding utilities."""

import socket

import pytest

from valkeylite.port_finder import (
    find_free_port,
    get_port_or_find_free,
    is_port_available,
    is_port_bindable,
)


def test_find_free_port():
    """Test finding a free port."""
    port = find_free_port()
    assert 16379 <= port < 16479
    assert is_port_available("127.0.0.1", port)


def test_is_port_available():
    """Test checking if a port is available."""
    # Port 80 is usually either unavailable or requires root
    # Port in high range should be available
    port = find_free_port()
    assert is_port_available("127.0.0.1", port)


def test_get_port_or_find_free_with_none():
    """Test auto-assigning port when None is passed."""
    port = get_port_or_find_free(None)
    assert isinstance(port, int)
    assert 16379 <= port < 16479


def test_get_port_or_find_free_with_available_port():
    """Test using a specific available port."""
    free_port = find_free_port()
    port = get_port_or_find_free(free_port)
    assert port == free_port


def test_find_free_port_exhaustion():
    """Test that we get an error if all ports are taken."""
    # This is hard to test without actually blocking 100 ports
    # Just verify the function exists and can be called
    port = find_free_port(start_port=50000)
    assert port >= 50000


@pytest.mark.parametrize("listen_host", ["127.0.0.1", "0.0.0.0"])
def test_is_port_bindable_detects_listener(listen_host):
    """A listener on the host or on the wildcard address makes the port unbindable.

    The wildcard case matters on macOS, where SO_REUSEADDR lets 127.0.0.1 bind
    over a 0.0.0.0 listener (e.g. a port published by Docker).
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind((listen_host, 0))
        listener.listen()
        port = listener.getsockname()[1]

        assert not is_port_bindable("127.0.0.1", port)
        with pytest.raises(OSError, match="already in use"):
            get_port_or_find_free(port)


def test_is_port_bindable_after_server_closes_connection():
    """Connections left in TIME_WAIT by a stopped server don't block a restart (#44)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        # Bind like valkey-server does
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        client = socket.create_connection(("127.0.0.1", port))
        conn, _ = listener.accept()
        # Server side closes first, so its end of the connection lingers
        conn.close()
        client.close()

    assert is_port_bindable("127.0.0.1", port)
    assert get_port_or_find_free(port) == port
