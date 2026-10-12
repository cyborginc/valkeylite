#!/usr/bin/env bash
# Build a Linux wheel inside a manylinux_2_28 container and verify its glibc floor.
#
# Usage (from the repo root):
#   docker run --rm -v "$PWD:/io" quay.io/pypa/manylinux_2_28_x86_64 \
#       /io/scripts/build_manylinux_wheel.sh
#
# The valkey-server binary links against the glibc of the machine it is
# compiled on, so it must be built on glibc 2.28 (the manylinux_2_28 image,
# AlmaLinux 8) to actually run on RHEL 8 and other glibc 2.28 systems.
# The wheel is written to /io/dist/.
set -euo pipefail

SRC=/io
WORK=/tmp/valkeylite-src
MAX_GLIBC=2.28
PYTHON=/opt/python/cp313-cp313/bin/python

# Build from a clean copy so a host build/ cache (compiled against a newer
# glibc) can never leak into the wheel.
rm -rf "$WORK"
mkdir -p "$WORK"
tar -C "$SRC" --exclude=./build --exclude=./dist --exclude=./.git \
    --exclude='./src/valkeylite/_binaries' -cf - . | tar -C "$WORK" -xf -

cd "$WORK"
"$PYTHON" -m pip install --quiet --root-user-action=ignore build
"$PYTHON" -m build --wheel

wheel=$(ls dist/*.whl)
echo "Built $wheel"

# Fail if the bundled binary needs any glibc symbol newer than MAX_GLIBC.
check_dir=$(mktemp -d)
"$PYTHON" -m zipfile -e "$wheel" "$check_dir"
binary=$(find "$check_dir" -name valkey-server -type f)
required=$(objdump -T "$binary" | grep -o 'GLIBC_[0-9.]*' | sed 's/GLIBC_//' | sort -uV | tail -1)
echo "valkey-server requires glibc >= $required (limit: $MAX_GLIBC)"
if [ "$(printf '%s\n%s\n' "$required" "$MAX_GLIBC" | sort -V | tail -1)" != "$MAX_GLIBC" ]; then
    echo "ERROR: valkey-server needs glibc $required, newer than manylinux_${MAX_GLIBC/./_}" >&2
    objdump -T "$binary" | grep -E "GLIBC_[0-9.]+" | grep -vE "GLIBC_2\.([0-9]|1[0-9]|2[0-8])([^0-9]|$)" >&2 || true
    exit 1
fi

auditwheel show "$wheel"

mkdir -p "$SRC/dist"
cp "$wheel" "$SRC/dist/"
echo "Wheel written to $SRC/dist/$(basename "$wheel")"
