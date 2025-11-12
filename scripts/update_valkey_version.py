#!/usr/bin/env python3
"""Check for new Valkey and valkey-py releases and update versions."""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)


def get_current_valkey_version() -> str:
    """Get current Valkey version from pyproject.toml."""
    pyproject = Path("pyproject.toml").read_text()
    match = re.search(r'version = "([^"]+)"', pyproject)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def get_current_valkey_py_version() -> str | None:
    """Get current valkey-py version requirement from pyproject.toml."""
    pyproject = Path("pyproject.toml").read_text()
    # Look for valkey>=X.Y in optional dependencies
    match = re.search(r'"valkey>=([^"]+)"', pyproject)
    if match:
        return match.group(1)
    return None


def parse_version(version: str) -> tuple[int, ...]:
    """Parse version string into tuple for comparison."""
    # Remove 'v' prefix if present
    version = version.lstrip("v")
    # Handle version with suffixes like "8.0.0-rc1"
    version = version.split("-")[0]
    return tuple(map(int, version.split(".")))


def get_all_valkey_releases() -> list[dict]:
    """Get all Valkey releases from GitHub API."""
    url = "https://api.github.com/repos/valkey-io/valkey/releases"
    headers = {"Accept": "application/vnd.github.v3+json"}

    # Get GitHub token if available (increases rate limit)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        releases = response.json()

        # Filter to only stable releases (not pre-releases)
        stable_releases = [r for r in releases if not r["prerelease"] and not r["draft"]]

        return stable_releases
    except Exception as e:
        print(f"Error fetching Valkey releases: {e}")
        sys.exit(1)


def get_latest_valkey_py_version() -> str:
    """Get latest valkey-py version from PyPI."""
    url = "https://pypi.org/pypi/valkey/json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data["info"]["version"]
    except Exception as e:
        print(f"Error fetching valkey-py version from PyPI: {e}")
        sys.exit(1)


def find_unreleased_versions(current_version: str, all_releases: list[dict]) -> list[str]:
    """
    Find all Valkey versions newer than current that we haven't released.

    This handles the case where:
    - We're at 8.0.0
    - 9.0.0 is released (we release it, now at 9.0.0)
    - 8.0.1 is released as a security patch
    We should detect 8.0.1 even though we're at 9.0.0
    """
    current = parse_version(current_version)
    current_major_minor = current[:2]  # e.g., (8, 0)

    unreleased = []

    for release in all_releases:
        tag = release["tag_name"].lstrip("v")
        version_tuple = parse_version(tag)

        # Version is newer if it's > current_version
        if version_tuple > current:
            unreleased.append(tag)
            continue

        # Also check for patches to the same major.minor we're on
        # e.g., if we're on 8.0.0 and 8.0.1 exists
        release_major_minor = version_tuple[:2]
        if release_major_minor == current_major_minor and version_tuple > current:
            unreleased.append(tag)

    # Sort by version (newest first)
    unreleased.sort(key=parse_version, reverse=True)

    return unreleased


def should_update_valkey_py(current_min: str | None, latest: str) -> tuple[bool, str | None]:
    """
    Check if valkey-py should be updated.

    Returns: (should_update, new_min_version)
    """
    if not current_min:
        # No minimum specified, suggest adding one
        major_minor = ".".join(latest.split(".")[:2])
        return True, f"{major_minor}.0"

    current = parse_version(current_min)
    latest_parsed = parse_version(latest)

    # Update if there's a newer major or minor version
    # Keep same major.minor if only patch changed
    if latest_parsed[:2] > current[:2]:
        new_min = ".".join(map(str, latest_parsed[:2])) + ".0"
        return True, new_min

    return False, None


def update_files(
    valkey_version: str, valkey_py_min: str | None = None, dry_run: bool = False
) -> None:
    """Update version in all relevant files."""
    updates = []

    # Update pyproject.toml - project version
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()

    old_version_match = re.search(r'version = "([^"]+)"', content)
    if old_version_match:
        old_version = old_version_match.group(1)
        new_content = content.replace(f'version = "{old_version}"', f'version = "{valkey_version}"')

        if new_content != content:
            updates.append(f"pyproject.toml: {old_version} → {valkey_version}")
            if not dry_run:
                pyproject_path.write_text(new_content)
            content = new_content

    # Update pyproject.toml - valkey-py dependency
    if valkey_py_min:
        old_dep_match = re.search(r'"valkey>=([^"]+)"', content)
        if old_dep_match:
            old_dep_version = old_dep_match.group(1)
            new_content = re.sub(r'"valkey>=([^"]+)"', f'"valkey>={valkey_py_min}"', content)

            if new_content != content:
                updates.append(f"valkey-py dependency: >={old_dep_version} → >={valkey_py_min}")
                if not dry_run:
                    pyproject_path.write_text(new_content)

    # Update setup.py
    setup_path = Path("setup.py")
    setup_content = setup_path.read_text()

    old_setup_match = re.search(r'VALKEY_VERSION = "([^"]+)"', setup_content)
    if old_setup_match:
        old_setup_version = old_setup_match.group(1)
        new_setup_content = setup_content.replace(
            f'VALKEY_VERSION = "{old_setup_version}"',
            f'VALKEY_VERSION = "{valkey_version}"',
        )

        if new_setup_content != setup_content:
            updates.append(f"setup.py: {old_setup_version} → {valkey_version}")
            if not dry_run:
                setup_path.write_text(new_setup_content)

    # Update src/valkey_server/__init__.py
    init_path = Path("src/valkey_server/__init__.py")
    init_content = init_path.read_text()

    old_init_match = re.search(r'__version__ = "([^"]+)"', init_content)
    if old_init_match:
        old_init_version = old_init_match.group(1)
        new_init_content = init_content.replace(
            f'__version__ = "{old_init_version}"', f'__version__ = "{valkey_version}"'
        )

        if new_init_content != init_content:
            updates.append(f"__init__.py: {old_init_version} → {valkey_version}")
            if not dry_run:
                init_path.write_text(new_init_content)

    # Print summary
    if updates:
        print("Updates" + (" (DRY RUN)" if dry_run else "") + ":")
        for update in updates:
            print(f"  ✓ {update}")
    else:
        print("No updates needed")

    return len(updates) > 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check for new Valkey and valkey-py releases")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument(
        "--github-output",
        help="Path to GitHub Actions output file",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Checking for Valkey and valkey-py updates")
    print("=" * 60)

    # Get current versions
    current_valkey = get_current_valkey_version()
    current_valkey_py = get_current_valkey_py_version()

    print(f"\nCurrent Valkey version: {current_valkey}")
    print(f"Current valkey-py requirement: >={current_valkey_py or 'none'}")

    # Get all Valkey releases
    print("\nFetching Valkey releases from GitHub...")
    all_releases = get_all_valkey_releases()
    print(f"Found {len(all_releases)} stable Valkey releases")

    # Find unreleased versions
    unreleased = find_unreleased_versions(current_valkey, all_releases)

    if unreleased:
        print(f"\n⚠️  Found {len(unreleased)} unreleased Valkey version(s):")
        for version in unreleased:
            print(f"  - {version}")

        # Use the newest unreleased version
        target_valkey = unreleased[0]
        print(f"\n→ Will update to: {target_valkey}")
    else:
        print("\n✓ Valkey is up to date")
        target_valkey = None

    # Check valkey-py
    print("\nFetching latest valkey-py from PyPI...")
    latest_valkey_py = get_latest_valkey_py_version()
    print(f"Latest valkey-py version: {latest_valkey_py}")

    should_update_py, new_valkey_py_min = should_update_valkey_py(
        current_valkey_py, latest_valkey_py
    )

    if should_update_py:
        print(f"→ Will update valkey-py requirement to: >={new_valkey_py_min}")
    else:
        print("✓ valkey-py is up to date")
        new_valkey_py_min = None

    # Perform updates
    if target_valkey or new_valkey_py_min:
        print("\n" + "=" * 60)
        update_version = target_valkey or current_valkey
        has_updates = update_files(update_version, new_valkey_py_min, args.dry_run)

        # Write GitHub Actions outputs
        if args.github_output and has_updates:
            with open(args.github_output, "a") as f:
                f.write("update_needed=true\n")
                f.write(f"valkey_version={update_version}\n")
                f.write(f"current_version={current_valkey}\n")
                if new_valkey_py_min:
                    f.write(f"valkey_py_version={new_valkey_py_min}\n")

                # Create PR body
                pr_body_lines = [
                    "## Automated Version Update\n",
                ]

                if target_valkey:
                    pr_body_lines.append(
                        f"Updates bundled Valkey from **{current_valkey}** to **{target_valkey}**\n"
                    )
                    if len(unreleased) > 1:
                        pr_body_lines.append(
                            f"\n**Note:** There are {len(unreleased)} unreleased Valkey versions. "
                            f"Consider releasing all of them:\n"
                        )
                        for v in unreleased:
                            pr_body_lines.append(f"- {v}\n")

                if new_valkey_py_min:
                    pr_body_lines.append(
                        f"\nUpdates valkey-py requirement to **>={new_valkey_py_min}**\n"
                    )

                pr_body_lines.append("\n### Valkey Release Notes\n")
                if target_valkey:
                    pr_body_lines.append(
                        f"https://github.com/valkey-io/valkey/releases/tag/{target_valkey}\n"
                    )

                pr_body_lines.append("\n### valkey-py Release Notes\n")
                pr_body_lines.append("https://github.com/valkey-io/valkey-py/releases\n")

                pr_body = "".join(pr_body_lines)
                # Escape newlines for GitHub Actions
                pr_body_escaped = pr_body.replace("\n", "%0A")
                f.write(f"pr_body={pr_body_escaped}\n")

            print(f"\n✓ Wrote outputs to {args.github_output}")

        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✓ Everything is up to date!")
        print("=" * 60)

        if args.github_output:
            with open(args.github_output, "a") as f:
                f.write("update_needed=false\n")

        sys.exit(0)


if __name__ == "__main__":
    main()
