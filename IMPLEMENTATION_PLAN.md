# Valkey-Server Python Implementation Plan

## Project Specifications

**Platforms:**
- Linux: x86_64, aarch64
- macOS: x86_64 (Intel), arm64 (Apple Silicon)
- Windows: Never

**Python Support:** 3.10, 3.11, 3.12, 3.13 (+ 3.14 when released)

**Build System:** setuptools + custom build hook (calls make directly)

**Package Name:** `valkey-server`

**License:** MIT

**Versioning:** Match Valkey version directly (e.g., 8.0.0)

---

## Why Build This? (vs. Alternatives)

### Comparison with Redislite

**Redislite status:**
- Last release: December 2023 (1+ year old)
- Redis version: 6.2 (released 2021, 2+ years behind)
- Platforms: Linux/macOS x86_64 only (no ARM64)
- 31 open issues, slow maintenance

**Our advantages:**
1. **Valkey 8.x** - Latest features, performance, security patches
2. **ARM64 support** - macOS M1/M2/M3, AWS Graviton, modern servers
3. **Open source licensing** - Valkey (BSD-3) vs Redis (SSPL/RSALv2)
4. **Modern Python** - 3.10+ focus with latest features
5. **Simpler architecture** - Server-only, users choose their client
6. **Active maintenance** - Daily auto-update checks, automated CI

### Design Philosophy

**Redislite approach:** Monolithic (server + client wrapper)
```python
import redislite
r = redislite.Redis()  # Both server AND client
r.set('key', 'value')
```

**Our approach:** Composable (server-only with optional client helper)
```python
from valkey_server import ValkeyServer

# Core: bring your own client
with ValkeyServer() as server:
    import valkey
    client = valkey.Valkey(**server.connection_kwargs)

# Optional: convenience wrapper
with ValkeyServer() as server:
    client = server.client()  # Requires: pip install valkey-server[client]
```

**Benefits:**
- Users can choose any client library (valkey-py, redis-py, aredis, etc.)
- Smaller core package (no forced dependencies)
- Single responsibility principle
- Better testability
- Uses valkey-py by default (official Valkey client)

### Target Use Cases

✅ **Perfect for:**
- Integration testing
- Local development
- CI/CD pipelines
- Temporary data processing
- Modern ARM64 environments

❌ **Not for:**
- Production deployments (use Docker/system packages)
- Windows (no plans to support)
- Redis 6.x specific features (Valkey diverges over time)

---

## Phase 1: Project Scaffolding & Build System

### 1.1 Repository Structure
```
valkey-server-py/
├── .github/
│   ├── workflows/
│   │   ├── check-valkey-release.yml    # Daily Valkey version check
│   │   ├── pr-tests.yml                # PR: build single wheel + test
│   │   ├── main-tests.yml              # Main: build all wheels + test
│   │   └── release.yml                 # Tag trigger: build + publish
│   └── dependabot.yml
├── src/
│   └── valkey_server/
│       ├── __init__.py                 # ValkeyServer class export
│       ├── __main__.py                 # CLI entry point
│       ├── server.py                   # Main ValkeyServer class
│       ├── client.py                   # Optional client wrapper (requires redis-py)
│       ├── config.py                   # Config generation
│       ├── exceptions.py               # Custom exceptions
│       ├── port_finder.py              # Free port detection
│       ├── pytest_plugin.py            # Pytest fixtures (optional)
│       └── _binary.py                  # Binary path resolution
├── tests/
│   ├── __init__.py
│   ├── test_server.py                  # Core functionality
│   ├── test_config.py                  # Configuration
│   ├── test_cli.py                     # CLI interface
│   └── conftest.py                     # Pytest fixtures
├── scripts/
│   └── update_valkey_version.py        # For auto-update workflow
├── setup.py                            # Custom build hook (downloads & compiles Valkey)
├── pyproject.toml                      # Modern Python packaging
├── README.md
├── LICENSE (MIT)
├── .gitignore
└── CHANGELOG.md
```

### 1.2 pyproject.toml Setup
**Build system:**
- `setuptools` - Standard build backend
- `wheel` - For wheel generation
- Build-time dependencies only (no CMake needed)

**Optional dependencies:**
```toml
[project.optional-dependencies]
client = ["valkey >= 6.0"]  # Official Valkey Python client (forked from redis-py)
pytest = ["pytest >= 7.0", "valkey >= 6.0"]
test = ["pytest >= 7.0", "pytest-timeout", "valkey >= 6.0"]
```

**Note:** We use `valkey-py` (PyPI package: `valkey`) as the default client library. It's the official Valkey Python client, forked from redis-py with identical API. Both redis-py and valkey-py work interchangeably with Valkey servers.

**Build configuration:**
- Custom build hook in `setup.py` downloads Valkey source
- Calls `make` directly to compile Valkey
- Bundle binary in package data
- Platform-specific wheel tags

### 1.3 setup.py Build Strategy
**Goals:**
1. Download Valkey source tarball at build time
2. Extract and compile using Valkey's native Makefile
3. Copy `valkey-server` binary to `src/valkey_server/_binaries/{platform}-{arch}/`
4. Strip symbols to reduce binary size
5. Set executable permissions

**Build process:**
```python
# setup.py
import subprocess
import urllib.request
import tarfile
import platform
import shutil
from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py

VALKEY_VERSION = "8.0.0"

class BuildValkeyCommand(build_py):
    def run(self):
        # Download Valkey source
        url = f"https://github.com/valkey-io/valkey/archive/refs/tags/{VALKEY_VERSION}.tar.gz"
        tarball = Path("build/valkey.tar.gz")
        tarball.parent.mkdir(exist_ok=True)

        urllib.request.urlretrieve(url, tarball)

        # Extract
        with tarfile.open(tarball) as tf:
            tf.extractall("build/")

        # Compile with make
        valkey_dir = Path(f"build/valkey-{VALKEY_VERSION}")
        subprocess.run(
            ["make", "-j$(nproc)", "valkey-server"],
            cwd=valkey_dir,
            check=True
        )

        # Determine platform
        system = platform.system().lower()
        machine = platform.machine()
        if machine == "arm64":
            machine = "aarch64" if system == "linux" else "arm64"

        # Copy binary to package
        target_dir = Path(f"src/valkey_server/_binaries/{system}-{machine}")
        target_dir.mkdir(parents=True, exist_ok=True)

        binary_src = valkey_dir / "src" / "valkey-server"
        binary_dst = target_dir / "valkey-server"
        shutil.copy2(binary_src, binary_dst)

        # Strip symbols
        subprocess.run(["strip", str(binary_dst)], check=True)
        binary_dst.chmod(0o755)

        # Continue with normal build
        super().run()

setup(cmdclass={"build_py": BuildValkeyCommand})
```

**Compilation options:**
- Use Valkey's default Makefile (handles jemalloc, dependencies)
- No TLS initially (reduce dependencies)
- Strip symbols with `strip` command to reduce size (~3-5MB → ~2MB)

---

## Phase 2: Core Python Implementation

### 2.1 ValkeyServer Class (`server.py`)

**API Design:**
```python
class ValkeyServer:
    def __init__(
        self,
        port: Optional[int] = None,        # None = auto-assign
        host: str = "127.0.0.1",
        data_dir: Optional[Path] = None,   # None = temp dir
        config: Optional[Dict[str, Any]] = None,
        persist: bool = False,              # True = keep data_dir
        **config_overrides
    ):
        """
        Initialize Valkey server instance.

        Args:
            port: Port to bind (None for auto-assign)
            host: Host to bind
            data_dir: Data directory (None for temp)
            config: Dict of Valkey config options
            persist: Keep data_dir after shutdown
            **config_overrides: Additional config options
        """

    def start(self, timeout: float = 10.0) -> None:
        """Start server and wait until ready."""

    def stop(self, timeout: float = 5.0) -> None:
        """Graceful shutdown."""

    def terminate(self) -> None:
        """Force kill."""

    def is_running(self) -> bool:
        """Check if process is alive and responding."""

    def wait_until_ready(self, timeout: float = 10.0) -> None:
        """Block until server accepts connections."""

    def __enter__(self) -> "ValkeyServer":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()

    @property
    def connection_url(self) -> str:
        """Return redis://host:port connection string."""

    @property
    def connection_kwargs(self) -> Dict[str, Any]:
        """Return kwargs dict for valkey-py client."""
        return {"host": self.host, "port": self.port}

    def client(self, **kwargs) -> "valkey.Valkey":
        """
        Create valkey-py client connected to this server.

        Requires: pip install valkey-server[client]

        Args:
            **kwargs: Additional kwargs passed to valkey.Valkey()

        Returns:
            valkey.Valkey instance connected to this server
        """

    # Internal methods
    def _find_binary(self) -> Path:
        """Locate platform-specific valkey-server binary."""

    def _generate_config(self) -> Path:
        """Generate temp config file."""

    def _cleanup(self) -> None:
        """Remove temp files/dirs."""
```

**Key Implementation Details:**
- Use `subprocess.Popen` for process management
- PID file tracking
- SIGTERM for graceful shutdown, SIGKILL as fallback
- Socket check for readiness (try connect)
- Automatic cleanup with `atexit` registration
- Thread-safe operations

### 2.2 Configuration Management (`config.py`)

**Default config for testing:**
```python
DEFAULT_CONFIG = {
    'bind': '127.0.0.1',
    'port': '{port}',                    # Template substitution
    'daemonize': 'no',
    'protected-mode': 'yes',
    'dir': '{data_dir}',
    'save': '',                          # Disable RDB
    'appendonly': 'no',                  # Disable AOF
    'logfile': '',                       # stdout
    'loglevel': 'notice',
}

def generate_config_file(
    base_config: Dict[str, Any],
    overrides: Dict[str, Any],
    output_path: Path
) -> None:
    """Generate valkey.conf file with merged settings."""
```

**Allow full Valkey config passthrough** for advanced users.

### 2.3 Binary Resolution (`_binary.py`)

```python
def get_binary_path() -> Path:
    """
    Find platform-specific valkey-server binary.

    Returns bundled binary based on:
    - platform.system() -> linux, darwin
    - platform.machine() -> x86_64, aarch64, arm64

    Raises:
        RuntimeError: If platform unsupported or binary not found
    """

def get_binary_name() -> str:
    """Return expected binary filename for current platform."""
```

**Binary locations:**
- `valkey_server/_binaries/linux-x86_64/valkey-server`
- `valkey_server/_binaries/linux-aarch64/valkey-server`
- `valkey_server/_binaries/darwin-x86_64/valkey-server`
- `valkey_server/_binaries/darwin-arm64/valkey-server`

### 2.4 Optional Client Wrapper (`client.py`)

**Requires:** `pip install valkey-server[client]`

**Implementation in ValkeyServer:**
```python
# In server.py
class ValkeyServer:
    def client(self, **kwargs):
        """Create valkey-py client connected to this server."""
        try:
            import valkey
        except ImportError:
            raise ImportError(
                "valkey-py required for client() method. "
                "Install with: pip install valkey-server[client]"
            ) from None

        return valkey.Valkey(
            host=self.host,
            port=self.port,
            **kwargs
        )
```

**Usage patterns:**
```python
# Basic usage with valkey-py
with ValkeyServer() as server:
    client = server.client()
    client.set('key', 'value')

# With client options
with ValkeyServer() as server:
    client = server.client(decode_responses=True, socket_timeout=5)
    client.set('key', 'value')

# Using custom client library (any Redis-compatible client)
with ValkeyServer() as server:
    import valkey
    client = valkey.Valkey(**server.connection_kwargs)

    # Or even redis-py if needed for compatibility
    import redis
    client = redis.Redis(**server.connection_kwargs)
```

### 2.5 Pytest Plugin (`pytest_plugin.py`)

**Requires:** `pip install valkey-server[pytest]`

**Auto-discovery:** Register in pyproject.toml:
```toml
[project.entry-points.pytest11]
valkey = "valkey_server.pytest_plugin"
```

**Fixtures provided:**
```python
# pytest_plugin.py
import pytest
from valkey_server import ValkeyServer

@pytest.fixture
def valkey_server():
    """Provide ValkeyServer instance for a test."""
    with ValkeyServer() as server:
        yield server

@pytest.fixture
def valkey_client(valkey_server):
    """Provide connected valkey-py client."""
    try:
        import valkey
    except ImportError:
        pytest.skip("valkey-py not installed")

    return valkey_server.client()

@pytest.fixture
def valkey_url(valkey_server):
    """Provide connection URL string."""
    return valkey_server.connection_url
```

**Usage in tests:**
```python
def test_with_server(valkey_server):
    """Test with server instance, bring your own client."""
    import valkey
    client = valkey.Valkey(host=valkey_server.host, port=valkey_server.port)
    client.set('key', 'value')
    assert client.get('key') == b'value'

def test_with_client(valkey_client):
    """Test with pre-configured valkey-py client."""
    valkey_client.set('key', 'value')
    assert valkey_client.get('key') == b'value'
```

### 2.6 CLI Interface (`__main__.py`)

**Phase 2: Minimal CLI (can expand later)**
```bash
# Run in foreground (for quick testing)
python -m valkey_server

# With options
python -m valkey_server --port 6380 --loglevel debug
```

**Later expansion:**
```bash
# Daemonized service mode
python -m valkey_server start [--config valkey.conf]
python -m valkey_server stop
python -m valkey_server status
python -m valkey_server restart
```

Use `argparse` initially, can switch to `click` if CLI grows complex.

---

## Phase 3: Build & CI/CD Workflows

### 3.1 Workflow: PR Tests (`pr-tests.yml`)

**Trigger:** Pull request to `main`

**Jobs:**
1. **Quick Build & Test** (single platform)
   - OS: `ubuntu-22.04`
   - Python: `3.13`
   - Arch: `x86_64`

**Steps:**
```yaml
- Checkout code
- Setup Python 3.13
- Install build dependencies (build-essential, make)
- Build wheel with `python -m build`
- Install wheel with [test] extras
- Run pytest
- Upload wheel as artifact (for manual inspection)
```

**Purpose:** Fast feedback (~5-10 min) before full build

### 3.2 Workflow: Main Branch Tests (`main-tests.yml`)

**Trigger:** Push to `main`

**Jobs:** Matrix build
- **Linux x86_64**: Python 3.10, 3.11, 3.12, 3.13
- **Linux aarch64**: Python 3.10, 3.11, 3.12, 3.13 (use `qemu` or ARM runners)
- **macOS x86_64**: Python 3.10, 3.11, 3.12, 3.13 (use `macos-13`)
- **macOS arm64**: Python 3.10, 3.11, 3.12, 3.13 (use `macos-14`)

**Steps per job:**
```yaml
- Checkout code
- Setup Python ${{ matrix.python-version }}
- Install build dependencies
- Build wheel
- Install wheel
- Run full test suite
- Upload wheel artifacts
```

**ARM64 Linux Strategy:**
- Option A: Use `qemu-user-static` (slow but free)
- Option B: Use GitHub ARM runners (beta, faster)
- Option C: Use `cibuildwheel` with cross-compilation

### 3.3 Workflow: Valkey Version Check (`check-valkey-release.yml`)

**Trigger:** Daily cron (`0 0 * * *` = midnight UTC)

**Logic:**
```python
# scripts/update_valkey_version.py

import re
import requests
from pathlib import Path

def get_latest_valkey_version() -> str:
    """Fetch latest release from GitHub API."""
    resp = requests.get("https://api.github.com/repos/valkey-io/valkey/releases/latest")
    data = resp.json()
    tag = data["tag_name"]  # e.g., "8.0.1"
    return tag.lstrip('v')

def get_current_version() -> str:
    """Read version from pyproject.toml."""
    content = Path("pyproject.toml").read_text()
    match = re.search(r'version = "([^"]+)"', content)
    return match.group(1)

def update_version_in_files(new_version: str):
    """Update version in pyproject.toml and setup.py."""
    # Update pyproject.toml version field
    # Update setup.py VALKEY_VERSION constant
    # Update CHANGELOG.md with new version header

if __name__ == "__main__":
    latest = get_latest_valkey_version()
    current = get_current_version()

    if latest != current:
        update_version_in_files(latest)
        print(f"Updated to {latest}")
    else:
        print("Already up to date")
```

**Workflow steps:**
```yaml
- Checkout code
- Run update_valkey_version.py
- If changes detected:
  - Create new branch: auto-update-valkey-{version}
  - Commit changes
  - Create PR with:
    - Title: "Update Valkey to {version}"
    - Body: Link to Valkey release notes
    - Labels: "dependencies", "automated"
```

### 3.4 Workflow: Release (`release.yml`)

**Trigger:** Tag push matching `v*` (e.g., `v8.0.0`)

**Jobs:**

1. **Build All Wheels** (matrix like main-tests.yml)
   - 4 platforms × 4 Python versions = 16 wheels
   - Upload to artifact storage

2. **Build Source Distribution**
   - `python -m build --sdist`
   - Contains full source + setup.py build hook
   - Users can build from source if wheel unavailable

3. **Create GitHub Release**
   - Extract tag version
   - Generate changelog from commits since last tag
   - Attach all wheel files + sdist

4. **Publish to PyPI** (requires approval)
   - Environment: `prod` (has branch protection)
   - Use trusted publishing (OIDC) or API token
   - Upload with `twine`

**Version Extraction:**
```yaml
- name: Get version from tag
  id: version
  run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT
```

---

## Phase 4: Testing Strategy

### 4.1 Test Dependencies
```toml
[project.optional-dependencies]
test = [
    "pytest >= 7.0",
    "pytest-timeout",
    "valkey >= 6.0",  # Python client for integration tests
]
```

### 4.2 Test Cases

**test_server.py:**
```python
def test_basic_lifecycle():
    """Start, check running, stop."""

def test_context_manager():
    """Ensure proper cleanup with context manager."""

def test_custom_port():
    """Specify port explicitly."""

def test_auto_port():
    """Auto-assign free port."""

def test_connection():
    """Connect with valkey-py client and perform SET/GET."""

def test_persist_data():
    """Persist data directory across restarts."""

def test_temp_data():
    """Temp directory cleanup."""

def test_multiple_instances():
    """Run multiple servers simultaneously."""

def test_graceful_shutdown():
    """SIGTERM sends shutdown signal."""

def test_force_terminate():
    """SIGKILL on timeout."""

def test_wait_until_ready():
    """Block until server accepts connections."""

def test_already_started():
    """Error on double start."""

def test_not_started():
    """Error on stop before start."""

def test_client_wrapper():
    """Test server.client() method returns valkey.Valkey instance."""

def test_client_without_valkey_py():
    """Verify helpful error when valkey-py not installed."""

def test_connection_kwargs():
    """Test connection_kwargs property."""
```

**test_config.py:**
```python
def test_default_config():
    """Verify safe defaults."""

def test_custom_config():
    """Override config options."""

def test_config_file_generation():
    """Generate valid valkey.conf syntax."""

def test_invalid_config():
    """Handle invalid config gracefully."""
```

**test_cli.py:**
```python
def test_cli_basic():
    """Run CLI in subprocess."""

def test_cli_custom_port():
    """Pass --port argument."""
```

**test_pytest_plugin.py:**
```python
def test_valkey_server_fixture(valkey_server):
    """Test the valkey_server fixture."""

def test_valkey_client_fixture(valkey_client):
    """Test the valkey_client fixture."""

def test_valkey_url_fixture(valkey_url):
    """Test the valkey_url fixture."""
```

### 4.3 CI Test Matrix Coverage

**Fast (PR):** 1 configuration (Ubuntu x86_64, Python 3.13)

**Full (main + release):** 16 configurations
- Linux x86_64: 3.10, 3.11, 3.12, 3.13
- Linux aarch64: 3.10, 3.11, 3.12, 3.13
- macOS x86_64: 3.10, 3.11, 3.12, 3.13
- macOS arm64: 3.10, 3.11, 3.12, 3.13

---

## Phase 5: Documentation

### 5.1 README.md Structure
```markdown
# valkey-server

Install and run Valkey directly from Python.

## Installation
`pip install valkey-server`

## Quick Start
[Context manager example]

## Use Cases
- Unit/integration testing
- Local development
- CI/CD pipelines
- Temporary data processing

## NOT for Production
[Clear warning about using Docker/system packages in production]

## Requirements
- Python 3.10+
- Linux (x86_64, aarch64) or macOS (x86_64, arm64)

## API Reference
[ValkeyServer class documentation]

## CLI Usage
[Command examples]

## Configuration
[Config options documentation]

## Platform Support
[Table of supported platforms]

## Contributing
## License (MIT)
## Changelog
```

### 5.2 Docstrings
- All public methods: Google style docstrings
- Type hints everywhere
- Examples in docstrings

### 5.3 Security Documentation
**Security considerations:**
- Binds to localhost by default
- Protected mode enabled
- No authentication by default (document how to add)
- Warn about binding to 0.0.0.0
- Version tracking for CVE awareness

---

## Phase 6: Release Process

### 6.1 Versioning Scheme
- **Match Valkey exactly**: `8.0.0`, `8.0.1`, etc.
- **If we need patches**: `8.0.0.post1` (rarely needed)

### 6.2 Release Checklist
1. Auto-update PR created (daily check)
2. Review Valkey changelog for breaking changes
3. PR tests pass (single wheel)
4. Merge to main
5. Main tests pass (all wheels)
6. Create tag: `git tag v8.0.0 && git push --tags`
7. Release workflow builds wheels
8. Manual approval at `prod` environment gate
9. Publish to PyPI
10. GitHub release created automatically

### 6.3 Post-Release
- Verify on PyPI: https://pypi.org/project/valkey-server/
- Test install: `pip install valkey-server=={version}`
- Update documentation if needed

---

## Implementation Order

### Sprint 1: Foundation (Days 1-3)
1. Repository structure
2. pyproject.toml with setuptools
3. setup.py build hook (download + compile Valkey with make)
4. Basic ValkeyServer class (start/stop)
5. Binary resolution logic
6. Manual build test on local machine

### Sprint 2: Core Features (Days 4-6)
1. Configuration management
2. Port auto-assignment
3. Temp directory handling
4. Context manager
5. Connection readiness check
6. Optional client wrapper (server.client())
7. Pytest plugin and fixtures
8. Basic tests

### Sprint 3: CI/CD (Days 7-9)
1. PR test workflow (single wheel)
2. Main test workflow (all wheels)
3. Fix platform-specific build issues
4. Test on all target platforms

### Sprint 4: Automation & Release (Days 10-12)
1. Valkey version check workflow
2. Auto-update script
3. Release workflow
4. PyPI publishing setup
5. Documentation
6. First release!

### Sprint 5: Polish (Days 13-14)
1. CLI implementation
2. Additional tests
3. Documentation improvements
4. Performance testing

---

## Technical Challenges & Solutions

### Challenge 1: Cross-Platform Compilation
**Problem:** Valkey's Makefile may behave differently across platforms

**Solution:**
- Use Valkey's native Makefile (it handles platform detection)
- Detect platform in setup.py to copy correct binary location
- Handle architecture naming differences (arm64 vs aarch64)
- Test on actual hardware (not just QEMU)
- Let Valkey handle jemalloc/dependencies automatically

### Challenge 2: Binary Size
**Problem:** Each wheel is 3-5MB

**Solution:**
- Strip debug symbols: `strip valkey-server`
- Compile with `-Os` (optimize size)
- Consider UPX compression (risky, can trigger antivirus)
- Accept the size (it's worth it for convenience)

### Challenge 3: ARM64 Linux Testing
**Problem:** GitHub doesn't have native ARM runners (yet)

**Solution:**
- Use QEMU for now (slow but works)
- Document manual testing process
- Consider Cirrus CI or other services with ARM

### Challenge 4: Valkey Dependencies
**Problem:** jemalloc, OpenSSL, systemd

**Solution:**
- jemalloc: Statically link or use system malloc
- OpenSSL: Skip TLS support initially
- systemd: Not needed for embedded use

### Challenge 5: Port Conflicts
**Problem:** Tests running in parallel may collide

**Solution:**
- Always auto-assign ports in tests
- Use socket binding to verify port free
- pytest-xdist support with unique ports

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Valkey security CVE | Medium | High | Auto-update workflow, clear version in metadata |
| Build failures on new platforms | Medium | Medium | Comprehensive CI matrix, good error messages |
| Binary not executable (permissions) | Low | High | Set +x in setup.py, test in CI |
| Port conflicts in tests | Medium | Low | Random port assignment, retry logic |
| Breaking changes in Valkey | Low | Medium | Review changelog before merge, semver |
| PyPI package size limit | Low | Low | ~40MB total well under 1GB limit |
| Licensing issues | Low | High | Use MIT, document Valkey's BSD-3-Clause |

---

## Success Criteria

**MVP (Minimum Viable Product):**
- Install with `pip install valkey-server`
- Works on Linux x86_64 and macOS arm64 (priority platforms)
- Context manager API functional
- Tests pass in CI
- One successful release to PyPI

**V1.0:**
- All 4 platforms supported
- Python 3.10-3.13 support
- Optional client wrapper (server.client()) working
- Pytest plugin with fixtures
- Auto-update workflow operational
- 90%+ test coverage
- Documentation complete
- CLI basics working

**Future:**
- Advanced CLI (daemon mode, service management)
- TLS support
- Authentication helpers
- Cluster mode support
- Redis/Valkey compatibility testing suite

---

## Package Installation Patterns

### Core Package (No Dependencies)
```bash
pip install valkey-server
```

```python
from valkey_server import ValkeyServer

# Bring your own client
with ValkeyServer() as server:
    # Use any Redis-compatible client
    pass
```

### With Client Wrapper
```bash
pip install valkey-server[client]
```

```python
from valkey_server import ValkeyServer

with ValkeyServer() as server:
    client = server.client()  # Returns valkey.Valkey instance
    client.set('key', 'value')
```

### With Pytest Fixtures
```bash
pip install valkey-server[pytest]
```

```python
# Automatically available in tests
def test_something(valkey_client):
    valkey_client.set('key', 'value')
    assert valkey_client.get('key') == b'value'
```

### Development/Testing (All Features)
```bash
pip install valkey-server[test]  # Includes client, pytest, testing tools
```

---

## Migration Path from Redislite

**Redislite code:**
```python
import redislite

r = redislite.Redis()
r.set('key', 'value')
assert r.get('key') == b'value'
```

**Equivalent with valkey-server:**
```python
from valkey_server import ValkeyServer

with ValkeyServer() as server:
    r = server.client()  # Returns valkey.Valkey instance
    r.set('key', 'value')
    assert r.get('key') == b'value'
```
*Requires: `pip install valkey-server[client]`*

**Or with explicit client choice:**
```python
from valkey_server import ValkeyServer
import valkey

with ValkeyServer() as server:
    r = valkey.Valkey(**server.connection_kwargs)
    r.set('key', 'value')
    assert r.get('key') == b'value'
```

**Or even redis-py for compatibility:**
```python
from valkey_server import ValkeyServer
import redis

with ValkeyServer() as server:
    # redis-py works too since Valkey is protocol-compatible
    r = redis.Redis(**server.connection_kwargs)
    r.set('key', 'value')
    assert r.get('key') == b'value'
```
