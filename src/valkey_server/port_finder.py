"""Utility to find available network ports."""

import socket
from typing import Optional


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
        f"Could not find an available port on {host} "
        f"in range {start_port}-{start_port + 99}"
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


def get_port_or_find_free(port: Optional[int], host: str = "127.0.0.1") -> int:
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

    if is_port_available(host, port):
        return port

    raise OSError(f"Port {port} is already in use on {host}")
