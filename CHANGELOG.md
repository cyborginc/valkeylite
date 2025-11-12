# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of valkeylite
- Embedded Valkey 9.0.0 server for Python
- Support for Linux (x86_64, aarch64) and macOS (x86_64, arm64)
- Python 3.10-3.13 support
- **Two APIs:**
  - Simple `Valkey` class - redislite-compatible, server auto-managed
  - Advanced `ValkeyServer` class - explicit server control
- valkey-py client included as core dependency
- Pytest fixtures (install with [test])
- CLI interface (`valkeylite` command)
- Automatic port assignment
- Temporary data directory with automatic cleanup
- Persistent data support via `dbfilename` parameter
- Configuration management with safe defaults
- Comprehensive API documentation

### Features
- Drop-in replacement for redislite (one-line code change)
- Dual API: Simple client wrapper + advanced server control
- ARM64 support for modern Apple Silicon and AWS Graviton
- Latest Valkey 9.0.0 server (not old Redis 6.2 like redislite)
- Safe localhost-only defaults
- Automatic binary resolution for current platform
- Platform-specific wheels (4 wheels, not 16)
- Static linking attempted for maximum portability

[Unreleased]: https://github.com/cyborginc/valkeylite/compare/v9.0.0...HEAD
