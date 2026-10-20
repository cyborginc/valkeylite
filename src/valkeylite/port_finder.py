"""Utility to find available network ports."""

import socket


def find_free_port(host: str = "127.0.0.1", start_port: int = 16379) -> int:
    """
    Find an available port on the specified host.

    Args:
        host: Host address to bind to (default: 127.0.0.1)
        start_port: Starting port to try (default: 16379)

    Returns:
        An available port number

    Raises:
        OSError: If no available port can be found after 100 attempts
    """
    for port in range(start_port, start_port + 100):
        if is_port_available(host, port):
            return port

    raise OSError(
        f"Could not find an available port on {host} in range {start_port}-{start_port + 99}"
    )


def is_port_available(host: str, port: int) -> bool:
    """
    Check if a port is available on the specified host.

    Args:
        host: Host address to check
        port: Port number to check

    Returns:
        True if port is available, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def is_port_bindable(host: str, port: int) -> bool:
    """
    Check if valkey-server could bind to a port on the specified host.

    valkey-server binds with SO_REUSEADDR, so a port is still usable while
    connections from a server that just stopped on it linger in TIME_WAIT.
    is_port_available() rejects such a port; this check does not.

    On macOS/BSD, SO_REUSEADDR also lets a specific address bind over a
    wildcard listener, so the wildcard address is checked too. Otherwise a port
    published on 0.0.0.0 (e.g. by Docker) would look free.

    Args:
        host: Host address to check
        port: Port number to check

    Returns:
        True if port can be bound, False otherwise
    """
    for address in dict.fromkeys((host, "0.0.0.0")):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((address, port))
            except OSError:
                return False
    return True


def get_port_or_find_free(port: int | None, host: str = "127.0.0.1") -> int:
    """
    Return the specified port if available, otherwise find a free one.

    Args:
        port: Desired port number, or None to auto-assign
        host: Host address to bind to

    Returns:
        Available port number

    Raises:
        OSError: If specified port is unavailable or no free port can be found
    """
    if port is None:
        return find_free_port(host)

    if is_port_bindable(host, port):
        return port

    raise OSError(f"Port {port} is already in use on {host}")
