"""Custom build script to download and compile Valkey."""

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

# Valkey version to bundle
VALKEY_VERSION = "8.0.1"


class BuildValkeyCommand(build_py):
    """Custom build command to download and compile Valkey."""

    def run(self):
        """Build Valkey binary and then run standard build."""
        self.announce("Downloading and building Valkey...", level=3)

        try:
            self.build_valkey()
        except Exception as e:
            self.warn(f"Failed to build Valkey: {e}")
            raise

        # Continue with standard build
        super().run()

    def build_valkey(self):
        """Download Valkey source and compile it."""
        # Create build directory
        build_dir = Path("build")
        build_dir.mkdir(exist_ok=True)

        # Download Valkey source
        tarball_path = build_dir / f"valkey-{VALKEY_VERSION}.tar.gz"
        if not tarball_path.exists():
            self.announce(f"Downloading Valkey {VALKEY_VERSION}...", level=3)
            url = (
                f"https://github.com/valkey-io/valkey/archive/"
                f"refs/tags/{VALKEY_VERSION}.tar.gz"
            )
            urllib.request.urlretrieve(url, tarball_path)
            self.announce("Download complete", level=3)
        else:
            self.announce("Using cached Valkey tarball", level=3)

        # Extract tarball
        valkey_src_dir = build_dir / f"valkey-{VALKEY_VERSION}"
        if not valkey_src_dir.exists():
            self.announce("Extracting Valkey source...", level=3)
            with tarfile.open(tarball_path, "r:gz") as tar:
                tar.extractall(build_dir)
            self.announce("Extraction complete", level=3)
        else:
            self.announce("Using cached Valkey source", level=3)

        # Compile Valkey
        self.announce("Compiling Valkey (this may take a few minutes)...", level=3)
        make_args = ["make", "-C", str(valkey_src_dir), "-j"]

        # Add parallel jobs based on CPU count
        try:
            import multiprocessing

            cpu_count = multiprocessing.cpu_count()
            make_args.append(str(cpu_count))
        except Exception:
            pass  # Fall back to make's default parallelism

        # Build just the server binary
        make_args.append("valkey-server")

        result = subprocess.run(make_args, capture_output=True, text=True)
        if result.returncode != 0:
            self.warn(f"Make stdout: {result.stdout}")
            self.warn(f"Make stderr: {result.stderr}")
            raise RuntimeError(f"Failed to compile Valkey: {result.stderr}")

        self.announce("Valkey compilation complete", level=3)

        # Determine target platform
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Normalize architecture naming
        if machine in ("x86_64", "amd64"):
            machine = "x86_64"
        elif machine in ("aarch64", "arm64"):
            if system == "linux":
                machine = "aarch64"
            else:  # darwin
                machine = "arm64"
        else:
            raise RuntimeError(
                f"Unsupported architecture: {machine}. "
                f"Supported: x86_64, aarch64, arm64"
            )

        if system not in ("linux", "darwin"):
            raise RuntimeError(
                f"Unsupported operating system: {system}. " f"Supported: Linux, macOS"
            )

        # Copy binary to package
        binary_src = valkey_src_dir / "src" / "valkey-server"
        target_dir = Path("src") / "valkey_server" / "_binaries" / f"{system}-{machine}"
        target_dir.mkdir(parents=True, exist_ok=True)
        binary_dst = target_dir / "valkey-server"

        self.announce(f"Copying binary to {binary_dst}...", level=3)
        shutil.copy2(binary_src, binary_dst)

        # Strip debug symbols to reduce size
        if shutil.which("strip"):
            self.announce("Stripping debug symbols...", level=3)
            try:
                subprocess.run(["strip", str(binary_dst)], check=True)
                self.announce("Binary stripped successfully", level=3)
            except subprocess.CalledProcessError:
                self.warn("Failed to strip binary (non-fatal)")

        # Set executable permissions
        binary_dst.chmod(0o755)

        # Get binary size
        size_mb = binary_dst.stat().st_size / (1024 * 1024)
        self.announce(
            f"Valkey binary ready: {binary_dst} ({size_mb:.1f} MB)", level=3
        )


# Run setup
if __name__ == "__main__":
    setup(
        cmdclass={
            "build_py": BuildValkeyCommand,
        }
    )
