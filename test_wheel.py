#!/usr/bin/env python
"""Comprehensive test script to verify the wheel works correctly."""

import socket
import sys

from valkey_server import ValkeyServer

print("Testing valkey-server package...")
print(f"Python: {sys.version}")

# Test 1: Basic server startup
print("\n1. Testing server startup & shutdown...")
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

# Test 2: Custom port
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

# Test 3: Connection properties
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

# Test 4: Redis protocol communication (raw socket)
print("\n4. Testing Redis protocol (raw socket)...")
try:
    with ValkeyServer() as server:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server.host, server.port))

        # Send PING command
        sock.send(b"*1\r\n$4\r\nPING\r\n")
        response = sock.recv(1024)

        assert b"+PONG" in response, f"Expected PONG, got: {response}"
        print(f"   ✓ Redis protocol works: {response.decode().strip()}")

        sock.close()
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 5: valkey-py client (if available)
print("\n5. Testing with valkey-py client...")
try:
    import valkey

    with ValkeyServer() as server:
        client = server.client()

        # Test basic operations
        client.set("test_key", "test_value")
        value = client.get("test_key")
        assert value == b"test_value", f"Expected b'test_value', got {value}"

        # Test numbers
        client.incr("counter")
        client.incr("counter")
        count = client.get("counter")
        assert count == b"2", f"Expected b'2', got {count}"

        print(f"   ✓ valkey-py client works (SET, GET, INCR)")

except ImportError:
    print("   ⚠ valkey-py not installed (optional), skipping client test")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 6: Multiple instances
print("\n6. Testing multiple server instances...")
try:
    with ValkeyServer() as server1:
        with ValkeyServer() as server2:
            assert server1.port != server2.port, "Servers should use different ports"
            assert server1.is_running() and server2.is_running()
            print(f"   ✓ Multiple instances work (ports: {server1.port}, {server2.port})")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 7: Binary is executable
print("\n7. Testing binary permissions...")
try:
    import os

    from valkey_server._binary import get_binary_path

    binary = get_binary_path()
    assert binary.exists(), f"Binary not found: {binary}"
    assert os.access(binary, os.X_OK), f"Binary not executable: {binary}"
    print(f"   ✓ Binary is executable: {binary}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 8: CLI interface
print("\n8. Testing CLI interface...")
try:
    import subprocess
    import time

    # Start server via CLI in background
    process = subprocess.Popen(
        [sys.executable, "-m", "valkey_server", "--port", "16385"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Give it a moment to start
    time.sleep(2)

    # Check if process is running
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        print(f"   ✗ CLI process died: {stderr}")
        sys.exit(1)

    # Try to connect to verify it's actually running
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    try:
        sock.connect(("127.0.0.1", 16385))
        sock.send(b"*1\r\n$4\r\nPING\r\n")
        response = sock.recv(1024)
        assert b"+PONG" in response
        print(f"   ✓ CLI started server successfully (PING response: {response.decode().strip()})")
    finally:
        sock.close()

    # Stop the server
    process.terminate()
    process.wait(timeout=5)
    print("   ✓ CLI interface works")

except Exception as e:
    # Make sure to cleanup
    if "process" in locals() and process.poll() is None:
        process.kill()
        process.wait()
    print(f"   ✗ Error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ All tests passed!")
print("=" * 60)
print("\nThe wheel is working correctly.")
