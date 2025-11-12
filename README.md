# valkey-server

[![PyPI version](https://img.shields.io/pypi/v/valkey-server.svg)](https://pypi.org/project/valkey-server/)
[![Python versions](https://img.shields.io/pypi/pyversions/valkey-server.svg)](https://pypi.org/project/valkey-server/)
[![License](https://img.shields.io/pypi/l/valkey-server.svg)](https://github.com/cyborginc/valkey-server-py/blob/main/LICENSE)
[![Sponsored by Cyborg Inc.](https://img.shields.io/badge/Sponsored%20by-Cyborg%20Inc.-blue)](https://www.cyborg.co)

**Install and run Valkey directly from Python**

`valkey-server` is a Python package that bundles the [Valkey](https://valkey.io/) server (the open-source continuation of Redis) as a library. It provides an embedded Valkey server that can be started and stopped from Python code, eliminating the need for external Valkey installations or Docker containers during development and testing.

It's like [`redislite`](https://github.com/yahoo/redislite) but with Valkey!

## Features

- 🚀 **Zero external dependencies** - No need to install Valkey separately
- 🔧 **Simple API** - Start/stop Valkey with a context manager
- 🧪 **Perfect for testing** - Isolated instances with auto-cleanup
- ⚡ **Latest Valkey** - Currently bundles Valkey 9.0.0
- 🔓 **Open source** - MIT license, bundles BSD-3-Clause Valkey

## Supported Platforms

| Platform | Architecture | Status |
|----------|--------------|--------|
| **Linux** | x86_64 | ✅ Supported |
| **Linux** | aarch64 (ARM64) | ✅ Supported |
| **macOS** | x86_64 (Intel) | ✅ Supported |
| **macOS** | arm64 (Apple Silicon) | ✅ Supported |
| **Windows** | - | ❌ Not supported |

## Installation

### Core Package (Server Only)

```bash
pip install valkey-server
```

### With Client Wrapper

```bash
pip install valkey-server[client]
```

Includes [valkey-py](https://github.com/valkey-io/valkey-py) client for convenience.

### For Testing/Development

```bash
pip install valkey-server[test]
```

Includes all optional dependencies for testing.

## Quick Start

### Basic Usage

```python
from valkey_server import ValkeyServer

# Start server (auto-assigns port)
with ValkeyServer() as server:
    print(f"Valkey running at {server.host}:{server.port}")

    # Use any Redis-compatible client
    import valkey
    client = valkey.Valkey(**server.connection_kwargs)
    client.set('key', 'value')
    assert client.get('key') == b'value'
# Server automatically stopped and cleaned up
```

### With Built-in Client Helper

```python
from valkey_server import ValkeyServer

with ValkeyServer() as server:
    # Convenience method (requires valkey-server[client])
    client = server.client()
    client.set('key', 'value')
    assert client.get('key') == b'value'
```

### Pytest Integration

```python
# Automatically available with valkey-server[test]

def test_with_server(valkey_server):
    """Use the server fixture."""
    import valkey
    client = valkey.Valkey(**valkey_server.connection_kwargs)
    client.set('test', 'data')
    assert client.get('test') == b'data'

def test_with_client(valkey_client):
    """Use the pre-configured client fixture."""
    valkey_client.set('test', 'data')
    assert valkey_client.get('test') == b'data'
```

### Command-Line Interface

```bash
# Start server in foreground
python -m valkey_server

# Specify port
python -m valkey_server --port 6380

# See all options
python -m valkey_server --help
```

## Advanced Usage

### Custom Configuration

```python
from valkey_server import ValkeyServer
from pathlib import Path

server = ValkeyServer(
    port=6380,                    # Specific port (None = auto-assign)
    host='127.0.0.1',            # Bind address
    data_dir=Path('/tmp/valkey'), # Data directory (None = temp)
    persist=True,                 # Keep data after shutdown
    config={
        'maxmemory': '100mb',
        'maxmemory-policy': 'allkeys-lru',
        'loglevel': 'debug',
    }
)

server.start()
# ... use server ...
server.stop()
```

### Multiple Instances

```python
from valkey_server import ValkeyServer

# Run multiple isolated servers
with ValkeyServer(port=6379) as server1:
    with ValkeyServer(port=6380) as server2:
        # Two independent Valkey instances
        client1 = server1.client()
        client2 = server2.client()
```

### Manual Lifecycle Management

```python
from valkey_server import ValkeyServer

server = ValkeyServer()
server.start(timeout=10.0)  # Wait up to 10s for startup

try:
    # Use server
    print(f"Server running: {server.is_running()}")
    print(f"Connection URL: {server.connection_url}")
finally:
    server.stop()  # Graceful shutdown
    # or server.terminate() for immediate kill
```

## API Reference

### ValkeyServer

```python
class ValkeyServer:
    def __init__(
        self,
        port: Optional[int] = None,
        host: str = "127.0.0.1",
        data_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        persist: bool = False,
        **config_overrides: Any,
    ) -> None:
        """Initialize Valkey server instance."""

    def start(self, timeout: float = 10.0) -> None:
        """Start server and wait until ready."""

    def stop(self, timeout: float = 5.0) -> None:
        """Gracefully stop server."""

    def terminate(self) -> None:
        """Force kill server."""

    def is_running(self) -> bool:
        """Check if server is running."""

    def wait_until_ready(self, timeout: float = 10.0) -> None:
        """Wait for server to accept connections."""

    def client(self, **kwargs: Any) -> valkey.Valkey:
        """Create valkey-py client (requires [client] extra)."""

    @property
    def port(self) -> int:
        """Get server port."""

    @property
    def connection_url(self) -> str:
        """Get redis:// connection URL."""

    @property
    def connection_kwargs(self) -> Dict[str, Any]:
        """Get connection parameters dict."""
```

### Pytest Fixtures

```python
# Available with pip install valkey-server[test]

@pytest.fixture
def valkey_server() -> ValkeyServer:
    """Provides ValkeyServer instance."""

@pytest.fixture
def valkey_client(valkey_server) -> valkey.Valkey:
    """Provides connected valkey-py client."""

@pytest.fixture
def valkey_url(valkey_server) -> str:
    """Provides connection URL string."""
```

## Development

```bash
# Clone repository
git clone https://github.com/cyborginc/valkey-server-py.git
cd valkey-server-py

# Install in development mode
pip install -e .[test]

# Run tests
pytest
```

## Contributing

Contributions welcome! Please:

1. Open an issue for bugs or feature requests
2. Submit PRs with tests and documentation
3. Follow existing code style

## License

MIT License - see [LICENSE](LICENSE) file

Valkey is licensed under BSD 3-Clause License

## Acknowledgments

This project is sponsored and maintained by [Cyborg Inc.](https://www.cyborg.co)

- Built on [Valkey](https://valkey.io/), the open-source continuation of Redis
- Inspired by [redislite](https://github.com/yahoo/redislite)
