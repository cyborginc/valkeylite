# valkeylite

[![PyPI version](https://img.shields.io/pypi/v/valkeylite.svg)](https://pypi.org/project/valkeylite/)
[![Python versions](https://img.shields.io/pypi/pyversions/valkeylite.svg)](https://pypi.org/project/valkeylite/)
[![License](https://img.shields.io/pypi/l/valkeylite.svg)](https://github.com/cyborginc/valkeylite/blob/main/LICENSE)
[![Sponsored by Cyborg Inc.](https://img.shields.io/badge/Sponsored%20by-Cyborg%20Inc.-blue)](https://www.cyborg.co)

**Install and run Valkey directly from Python**

`valkeylite` is a Python package that bundles the [Valkey](https://valkey.io/) server (the open-source continuation of Redis) as a library. It provides an embedded Valkey server that can be started and stopped from Python code, eliminating the need for external Valkey installations or Docker containers during development and testing.

It's like [`redislite`](https://github.com/yahoo/redislite) but with Valkey!

## Features

- 🚀 **Drop-in replacement** for redislite with Valkey
- 🔧 **Two APIs** - Simple client wrapper OR explicit server control
- 🧪 **Perfect for testing** - Isolated instances with auto-cleanup
- ⚡ **Latest Valkey** - Currently bundles Valkey 9.0.0
- 🎯 **Pytest fixtures** - Built-in pytest integration
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

```bash
pip install valkeylite
```

Includes valkey-py client automatically. For testing extras:

```bash
pip install valkeylite[test]
```

## Quick Start

### Client API (Like redislite)

```python
from valkeylite import Valkey

# Just works - server starts automatically
r = Valkey()
r.set('key', 'value')
assert r.get('key') == b'value'
r.close()

# Or with context manager
with Valkey() as r:
    r.set('key', 'value')
    assert r.get('key') == b'value'

# With persistence
r = Valkey('/tmp/mydata.db')
r.set('key', 'value')
r.close()
```

### Server API

```python
from valkeylite import ValkeyServer

# Full control over server lifecycle
with ValkeyServer() as server:
    print(f"Valkey running at {server.host}:{server.port}")

    # Use built-in client
    client = server.client()
    client.set('key', 'value')

    # Or bring your own (any Redis-compatible client)
    import aredis
    client = aredis.Redis(**server.connection_kwargs)
```

### Pytest Integration

```python
# Automatically available with valkeylite[test]

def test_with_server(valkeylite):
    """Use the server fixture."""
    import valkey
    client = valkey.Valkey(**valkeylite.connection_kwargs)
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
valkeylite

# Or with python -m
python -m valkeylite

# Specify port
valkeylite --port 6380

# See all options
valkeylite --help
```

## Advanced Usage

### Custom Configuration

```python
from valkeylite import ValkeyServer
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
from valkeylite import ValkeyServer

# Run multiple isolated servers
with ValkeyServer(port=6379) as server1:
    with ValkeyServer(port=6380) as server2:
        # Two independent Valkey instances
        client1 = server1.client()
        client2 = server2.client()
```

### Manual Lifecycle Management

```python
from valkeylite import ValkeyServer

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

### Valkey (Client API)

```python
class Valkey(valkey.Valkey):
    """
    Valkey client with embedded server (like redislite.Redis).

    Inherits all methods from valkey.Valkey client.
    """

    def __init__(
        self,
        dbfilename: Optional[Path] = None,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize client with embedded server.

        Args:
            dbfilename: Path for persistent data (None = temporary)
            host: Host to bind to
            port: Port to bind to (None = auto-assign)
            **kwargs: Additional valkey.Valkey arguments
        """

    @property
    def server(self) -> ValkeyServer:
        """Access underlying ValkeyServer instance."""
```

### ValkeyServer (Server API)

```python
class ValkeyServer:
    """Explicit server lifecycle management."""

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

    def client(self, **kwargs: Any) -> valkey.Valkey:
        """Create valkey-py client connected to this server."""

    @property
    def port(self) -> int:
        """Get server port."""

    @property
    def connection_kwargs(self) -> Dict[str, Any]:
        """Get connection parameters for any client."""
```

### Pytest Fixtures

```python
# Available with pip install valkeylite[test]

@pytest.fixture
def valkeylite() -> ValkeyServer:
    """Provides ValkeyServer instance."""

@pytest.fixture
def valkey_client(valkeylite) -> valkey.Valkey:
    """Provides connected valkey-py client."""

@pytest.fixture
def valkey_url(valkeylite) -> str:
    """Provides connection URL string."""
```

## Migration from redislite

```python
# Before
from redislite import Redis
r = Redis()
r.set('key', 'value')

# After
from valkeylite import Valkey
r = Valkey()
r.set('key', 'value')
```

**With persistence:**

```python
# Before
from redislite import Redis
r = Redis('/tmp/redis.db')

# After
from valkeylite import Valkey
r = Valkey('/tmp/redis.db')
```

## Development

```bash
# Clone repository
git clone https://github.com/cyborginc/valkeylite.git
cd valkeylite

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
