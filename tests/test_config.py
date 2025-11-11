"""Test configuration management."""

import tempfile
from pathlib import Path

import pytest

from valkey_server.config import DEFAULT_CONFIG, generate_config_file, validate_config
from valkey_server.exceptions import ValkeyConfigurationError


def test_default_config():
    """Test that default config has expected values."""
    assert DEFAULT_CONFIG["bind"] == "127.0.0.1"
    assert DEFAULT_CONFIG["protected-mode"] == "yes"
    assert DEFAULT_CONFIG["daemonize"] == "no"
    assert DEFAULT_CONFIG["save"] == ""
    assert DEFAULT_CONFIG["appendonly"] == "no"


def test_generate_config_file():
    """Test generating a config file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "valkey.conf"
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        generate_config_file(
            config_path=config_path,
            port=6379,
            data_dir=data_dir,
            config_overrides={"maxmemory": "100mb"},
        )

        assert config_path.exists()
        content = config_path.read_text()

        # Check that our values are in the config
        assert "port 6379" in content
        assert f"dir {data_dir}" in content
        assert "maxmemory 100mb" in content
        assert "bind 127.0.0.1" in content


def test_generate_config_with_empty_string():
    """Test that empty string values are handled correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "valkey.conf"
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        generate_config_file(
            config_path=config_path,
            port=6379,
            data_dir=data_dir,
            config_overrides={"save": ""},
        )

        content = config_path.read_text()
        assert 'save ""' in content


def test_validate_config_bind_zero():
    """Test that binding to 0.0.0.0 raises an error."""
    with pytest.raises(ValkeyConfigurationError, match="0.0.0.0"):
        validate_config({"bind": "0.0.0.0"})


def test_validate_config_daemonize():
    """Test that daemonize=yes raises an error."""
    with pytest.raises(ValkeyConfigurationError, match="daemonize"):
        validate_config({"daemonize": "yes"})


def test_validate_config_invalid_port():
    """Test that invalid port numbers raise an error."""
    with pytest.raises(ValkeyConfigurationError, match="Invalid port"):
        validate_config({"port": 70000})

    with pytest.raises(ValkeyConfigurationError, match="Invalid port"):
        validate_config({"port": 0})


def test_validate_config_valid():
    """Test that valid configurations pass validation."""
    # These should not raise
    validate_config({"bind": "127.0.0.1"})
    validate_config({"port": 6379})
    validate_config({"maxmemory": "100mb"})
    validate_config({})
