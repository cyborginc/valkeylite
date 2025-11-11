# valkey-server

[![PyPI version](https://img.shields.io/pypi/v/valkey-server.svg)](https://pypi.org/project/valkey-server/)
[![Python versions](https://img.shields.io/pypi/pyversions/valkey-server.svg)](https://pypi.org/project/valkey-server/)
[![License](https://img.shields.io/pypi/l/valkey-server.svg)](https://github.com/nicolaskruchten/valkey-server-py/blob/main/LICENSE)

**Install and run Valkey directly from Python** - perfect for testing and development.

`valkey-server` is a Python package that bundles the [Valkey](https://valkey.io/) server (the open-source continuation of Redis) as a library. It provides an embedded Valkey server that can be started and stopped from Python code, eliminating the need for external Valkey installations or Docker containers during development and testing.

## Features

- 🚀 **Zero external dependencies** - No need to install Valkey separately
- 🔧 **Simple API** - Start/stop Valkey with a context manager
- 🧪 **Perfect for testing** - Isolated instances with auto-cleanup
- 🏗️ **Modern platforms** - ARM64 support for Apple Silicon & AWS Graviton
- 🐍 **Modern Python** - Python 3.10-3.13 support
- ⚡ **Latest Valkey** - Currently bundles Valkey 8.0.1
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

### Core Package (Server Only)

```bash
pip install valkey-server
```

### With Client Wrapper

```bash
pip install valkey-server[client]
```

Includes [valkey-py](https://github.com/valkey-io/valkey-py) client for convenience.

### With Pytest Fixtures

```bash
pip install valkey-server[pytest]
```

Includes pytest fixtures for testing.

### All Features

```bash
pip install valkey-server[test]
```

Includes all optional dependencies.

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
# Automatically available with valkey-server[pytest]

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
# Available with pip install valkey-server[pytest]

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

## Why valkey-server?

### vs. Redislite

| Feature | valkey-server | redislite |
|---------|--------------|-----------|
| Server Version | **Valkey 8.0** | Redis 6.2 (2021) |
| ARM64 macOS | ✅ Yes | ❌ No |
| ARM64 Linux | ✅ Yes | ❌ No |
| License | MIT + BSD-3 (Valkey) | Valkey License |
| Last Updated | **Active** | Dec 2023 |
| Python | 3.10-3.13 | 3.8-3.12 |
| Design | Server-only, client optional | Monolithic wrapper |

### vs. Docker

**Use valkey-server when:**
- ✅ You want instant setup without Docker
- ✅ Running tests in CI/CD
- ✅ Developing locally without containers
- ✅ Need lightweight test fixtures

**Use Docker when:**
- ✅ Production deployments
- ✅ Need exact production parity
- ✅ Running clusters
- ✅ Complex multi-service setups

## Use Cases

✅ **Perfect for:**
- Unit and integration testing
- Local development
- CI/CD pipelines
- Temporary data processing
- Learning and experimentation

❌ **Not for:**
- Production deployments (use Docker or system packages)
- High-performance requirements (use dedicated Valkey installation)
- Clusters or replication (use proper Valkey deployment)

## Migration from redislite

```python
# Before (redislite)
import redislite
r = redislite.Redis()
r.set('key', 'value')

# After (valkey-server)
from valkey_server import ValkeyServer

with ValkeyServer() as server:
    r = server.client()
    r.set('key', 'value')
```

## Security Considerations

**Default configuration is secure for local development:**
- ✅ Binds to `127.0.0.1` (localhost only)
- ✅ Protected mode enabled
- ❌ No authentication (add with `config={'requirepass': 'secret'}`)

**For production or non-local use:**
- Configure authentication (`requirepass`)
- Use TLS if exposing over network
- Consider firewall rules
- Use proper Valkey deployment tools

## Troubleshooting

### Build Errors

If you encounter build errors during installation:

```bash
# Ensure you have build tools
# On Ubuntu/Debian:
sudo apt-get install build-essential

# On macOS:
xcode-select --install
```

### Port Already in Use

```python
# Let valkey-server auto-assign a port
with ValkeyServer(port=None) as server:  # None = auto
    print(f"Using port: {server.port}")
```

### Binary Not Found

If you get `ValkeyBinaryNotFoundError`, your platform may be unsupported or the installation was incomplete. Reinstall:

```bash
pip install --force-reinstall --no-cache-dir valkey-server
```

## Development

```bash
# Clone repository
git clone https://github.com/nicolaskruchten/valkey-server-py.git
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

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## Links

- **PyPI**: https://pypi.org/project/valkey-server/
- **GitHub**: https://github.com/nicolaskruchten/valkey-server-py
- **Valkey**: https://valkey.io/
- **valkey-py**: https://github.com/valkey-io/valkey-py

## Acknowledgments

- Built on [Valkey](https://valkey.io/), the open-source continuation of Redis
- Inspired by [redislite](https://github.com/yahoo/redislite)
- Thanks to the Valkey and Python communities
