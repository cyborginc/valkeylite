"""Custom build script to download and compile Valkey."""

import platform
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build_py import build_py

# Valkey version to bundle
VALKEY_VERSION = "8.0.1"


def get_platform_tag():
    """Get the proper platform tag for the wheel."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Normalize machine
    if machine in ("x86_64", "amd64"):
        machine = "x86_64"
    elif machine in ("aarch64", "arm64"):
        if system == "linux":
            machine = "aarch64"
        else:  # darwin
            machine = "arm64"

    if system == "linux":
        # Use manylinux_2_28 (compatible with glibc 2.28+, released 2018)
        # Works on: Ubuntu 20.04+, Debian 10+, RHEL 8+, etc.
        return f"manylinux_2_28_{machine}"
    elif system == "darwin":
        # macOS version minimums
        if machine == "arm64":
            return f"macosx_11_0_{machine}"  # macOS 11 Big Sur minimum for ARM64
        else:
            return f"macosx_10_13_{machine}"  # macOS 10.13 High Sierra minimum for x86_64
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


class BdistWheelCommand(bdist_wheel):
    """Custom bdist_wheel to set platform tag."""

    def finalize_options(self):
        """Set the platform name for the wheel."""
        super().finalize_options()
        # Override platform tag
        self.plat_name = get_platform_tag()
        self.plat_name_supplied = True


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
            url = f"https://github.com/valkey-io/valkey/archive/refs/tags/{VALKEY_VERSION}.tar.gz"
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

        # Compile Valkey with static linking
        self.announce(
            "Compiling Valkey with static linking (this may take a few minutes)...", level=3
        )

        # Determine number of parallel jobs
        try:
            import multiprocessing

            cpu_count = multiprocessing.cpu_count()
        except Exception:
            cpu_count = 1

        # Try static linking first
        # BUILD_TLS=no: Disable TLS to avoid OpenSSL dependency
        # MALLOC=libc: Use standard libc malloc instead of jemalloc (simpler)
        # These flags create a self-contained static binary
        static_make_args = [
            "make",
            "-C",
            str(valkey_src_dir),
            f"-j{cpu_count}",
            "BUILD_TLS=no",
            "MALLOC=libc",
            "valkey-server",
        ]

        # Add LDFLAGS for static linking on Linux
        system = platform.system().lower()
        if system == "linux":
            # Try full static linking on Linux
            static_make_args.insert(3, "LDFLAGS=-static")
            self.announce("Attempting full static linking on Linux...", level=3)

        result = subprocess.run(static_make_args, capture_output=True, text=True)

        if result.returncode != 0:
            # If static linking failed, try without -static flag
            if system == "linux" and "-static" in " ".join(static_make_args):
                self.announce("Full static linking failed, trying dynamic linking...", level=3)
                static_make_args = [arg for arg in static_make_args if arg != "LDFLAGS=-static"]
                result = subprocess.run(static_make_args, capture_output=True, text=True)

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
                f"Unsupported architecture: {machine}. Supported: x86_64, aarch64, arm64"
            )

        if system not in ("linux", "darwin"):
            raise RuntimeError(f"Unsupported operating system: {system}. Supported: Linux, macOS")

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
        self.announce(f"Valkey binary ready: {binary_dst} ({size_mb:.1f} MB)", level=3)

        # Check if binary is statically linked (Linux only)
        if system == "linux":
            self._check_binary_linking(binary_dst)

    def _check_binary_linking(self, binary_path):
        """Check if the binary is statically or dynamically linked."""
        try:
            result = subprocess.run(
                ["ldd", str(binary_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                # ldd succeeded, binary is dynamically linked
                self.announce("Binary is dynamically linked. Dependencies:", level=2)
                for line in result.stdout.split("\n"):
                    if line.strip():
                        self.announce(f"  {line}", level=2)
                self.announce(
                    "Note: For manylinux compatibility, you should run auditwheel:", level=2
                )
                self.announce("  auditwheel repair dist/*.whl", level=2)
            else:
                # ldd failed, likely statically linked
                self.announce("Binary appears to be statically linked (good!)", level=3)

        except FileNotFoundError:
            # ldd not available
            pass


# Run setup
if __name__ == "__main__":
    setup(
        cmdclass={
            "build_py": BuildValkeyCommand,
            "bdist_wheel": BdistWheelCommand,
        }
    )
