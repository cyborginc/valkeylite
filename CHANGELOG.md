# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of valkey-server
- Embedded Valkey 8.0.1 server for Python
- Support for Linux (x86_64, aarch64) and macOS (x86_64, arm64)
- Python 3.10-3.13 support
- Context manager API for easy server lifecycle management
- Optional valkey-py client wrapper (install with [client])
- Pytest fixtures (install with [test])
- CLI interface for running servers from command line
- Automatic port assignment
- Temporary data directory with automatic cleanup
- Configuration management with safe defaults
- Comprehensive API documentation

### Features
- Zero external dependencies for core functionality
- ARM64 support for modern Apple Silicon and AWS Graviton
- Latest Valkey 8.0.1 server (not old Redis 6.2 like redislite)
- Server-only design with optional client integration
- Safe localhost-only defaults
- Automatic binary resolution for current platform

[Unreleased]: https://github.com/cyborginc/valkey-server-py/compare/v8.0.1...HEAD
