"""CLI entry point for valkey-server."""

import argparse
import sys
from pathlib import Path
from typing import Any

from .server import ValkeyServer


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="valkey-server",
        description="Run an embedded Valkey server for development and testing",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to (default: auto-assign)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind to (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Directory for Valkey data files (default: temp directory)",
    )

    parser.add_argument(
        "--persist",
        action="store_true",
        help="Keep data directory after shutdown",
    )

    parser.add_argument(
        "--loglevel",
        type=str,
        choices=["debug", "verbose", "notice", "warning"],
        default="notice",
        help="Log level (default: notice)",
    )

    return parser.parse_args()


def main() -> int:
    """Main CLI entry point."""
    args = parse_args()

    # Build config from arguments
    config: dict[str, Any] = {
        "loglevel": args.loglevel,
    }

    try:
        print(f"Starting Valkey server on {args.host}:{args.port or 'auto'}...")

        server = ValkeyServer(
            port=args.port,
            host=args.host,
            data_dir=args.data_dir,
            config=config,
            persist=args.persist,
        )

        server.start()

        print("✓ Valkey server started successfully!")
        print(f"  Host: {server.host}")
        print(f"  Port: {server.port}")
        print(f"  Connection URL: {server.connection_url}")
        print(f"  Data directory: {server.data_dir}")
        print("\nPress Ctrl+C to stop the server...")

        # Keep running until interrupted
        try:
            while server.is_running():
                import time

                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nReceived interrupt, shutting down...")
            server.stop()
            print("✓ Server stopped")
            return 0

    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
