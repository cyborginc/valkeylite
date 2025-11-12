#!/usr/bin/env python
"""Quick test script to verify the wheel works."""

import sys

from valkey_server import ValkeyServer

print("Testing valkey-server package...")
print(f"Python: {sys.version}")

# Test basic server startup
print("\n1. Testing server startup...")
try:
    with ValkeyServer() as server:
        print(f"   ✓ Server started on {server.host}:{server.port}")
        print(f"   ✓ Connection URL: {server.connection_url}")
        print(f"   ✓ Server is running: {server.is_running()}")
        print(f"   ✓ Data directory: {server.data_dir}")
    print("   ✓ Server stopped cleanly")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test custom port
print("\n2. Testing custom port assignment...")
try:
    server = ValkeyServer(port=16380)
    server.start()
    assert server.port == 16380, f"Expected port 16380, got {server.port}"
    print(f"   ✓ Custom port {server.port} works")
    server.stop()
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test connection properties
print("\n3. Testing connection properties...")
try:
    with ValkeyServer() as server:
        kwargs = server.connection_kwargs
        assert "host" in kwargs and "port" in kwargs
        assert kwargs["host"] == server.host
        assert kwargs["port"] == server.port
        print(f"   ✓ Connection kwargs: {kwargs}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

print("\n✅ All tests passed!")
print("\nThe wheel is working correctly.")
