"""Binary resolution for platform-specific Valkey binaries."""

import platform
from pathlib import Path

from .exceptions import ValkeyBinaryNotFoundError


def get_platform_info() -> tuple[str, str]:
    """
    Get normalized platform and architecture information.

    Returns:
        Tuple of (system, machine) where:
        - system: 'linux' or 'darwin'
        - machine: 'x86_64', 'aarch64', or 'arm64'

    Raises:
        ValkeyBinaryNotFoundError: If platform is unsupported
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Normalize system name
    if system not in ("linux", "darwin"):
        raise ValkeyBinaryNotFoundError(
            f"Unsupported operating system: {system}. valkey-server supports Linux and macOS only."
        )

    # Normalize architecture name
    # Linux typically uses x86_64/aarch64
    # macOS can use x86_64/arm64
    if machine in ("x86_64", "amd64"):
        machine = "x86_64"
    elif machine in ("aarch64", "arm64"):
        # Keep platform-specific naming
        if system == "linux":
            machine = "aarch64"
        else:  # darwin
            machine = "arm64"
    else:
        raise ValkeyBinaryNotFoundError(
            f"Unsupported architecture: {machine}. valkey-server supports x86_64 and ARM64 only."
        )

    return system, machine


def get_binary_path() -> Path:
    """
    Get the path to the platform-specific Valkey server binary.

    Returns:
        Path to the valkey-server executable

    Raises:
        ValkeyBinaryNotFoundError: If binary cannot be found or platform is unsupported
    """
    system, machine = get_platform_info()

    # Determine binary directory
    package_dir = Path(__file__).parent
    binary_dir = package_dir / "_binaries" / f"{system}-{machine}"
    binary_path = binary_dir / "valkey-server"

    # Check if binary exists
    if not binary_path.exists():
        raise ValkeyBinaryNotFoundError(
            f"Valkey binary not found at {binary_path}. "
            f"Platform: {system}-{machine}. "
            f"This may indicate an incomplete installation or unsupported platform."
        )

    # Check if binary is executable
    if not binary_path.is_file():
        raise ValkeyBinaryNotFoundError(f"Valkey binary exists but is not a file: {binary_path}")

    return binary_path
