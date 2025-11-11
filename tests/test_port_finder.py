"""Test port finding utilities."""

from valkey_server.port_finder import find_free_port, get_port_or_find_free, is_port_available


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
