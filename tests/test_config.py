#!/usr/bin/env python3
"""Unit tests for configuration handling"""

import pytest
import tempfile
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after path modification
import tor_guard


class TestConfigParsing:
    """Test configuration file parsing."""

    def test_parse_default_config(self):
        """Test parsing default configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(tor_guard.DEFAULT_CFG)
            f.flush()
            temp_path = Path(f.name)

        try:
            cfg = tor_guard.parse_cfg(temp_path)

            assert cfg["SOCKS_PORTS"] == [9050, 9150]
            assert cfg["CHECK_HOSTS"] == ["127.0.0.1", "::1"]
            assert cfg["GRACE_SECONDS"] == 8
            assert cfg["RETRIES"] == 2
            assert cfg["CHECK_INTERVAL"] == 3
            assert cfg["REQUIRE_CONFIRM"] is True
            assert cfg["USE_TK"] is True
            assert cfg["USE_CURSES"] is True
        finally:
            temp_path.unlink()

    def test_parse_custom_ports(self):
        """Test parsing custom SOCKS ports."""
        config_text = "SOCKS_PORTS=9050,9150,9250\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(config_text)
            f.flush()
            temp_path = Path(f.name)

        try:
            cfg = tor_guard.parse_cfg(temp_path)
            assert cfg["SOCKS_PORTS"] == [9050, 9150, 9250]
        finally:
            temp_path.unlink()

    def test_parse_boolean_values(self):
        """Test parsing boolean configuration values."""
        test_cases = [
            ("true", True),
            ("false", False),
            ("yes", True),
            ("no", False),
            ("1", True),
            ("0", False),
            ("on", True),
            ("off", False),
        ]

        for value, expected in test_cases:
            config_text = f"REQUIRE_CONFIRM={value}\n"

            with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
                f.write(config_text)
                f.flush()
                temp_path = Path(f.name)

            try:
                cfg = tor_guard.parse_cfg(temp_path)
                assert cfg["REQUIRE_CONFIRM"] == expected, f"Failed for value: {value}"
            finally:
                temp_path.unlink()

    def test_parse_invalid_port(self):
        """Test parsing with invalid port numbers."""
        config_text = "SOCKS_PORTS=9050,invalid,9150\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(config_text)
            f.flush()
            temp_path = Path(f.name)

        try:
            cfg = tor_guard.parse_cfg(temp_path)
            # Should skip invalid values
            assert 9050 in cfg["SOCKS_PORTS"]
            assert 9150 in cfg["SOCKS_PORTS"]
        finally:
            temp_path.unlink()

    def test_parse_comments_ignored(self):
        """Test that comments are ignored."""
        config_text = """
# This is a comment
SOCKS_PORTS=9050
# Another comment
GRACE_SECONDS=10
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(config_text)
            f.flush()
            temp_path = Path(f.name)

        try:
            cfg = tor_guard.parse_cfg(temp_path)
            assert cfg["SOCKS_PORTS"] == [9050]
            assert cfg["GRACE_SECONDS"] == 10
        finally:
            temp_path.unlink()


class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_port_range(self):
        """Test port number validation."""
        assert tor_guard.validate_port(1) is True
        assert tor_guard.validate_port(9050) is True
        assert tor_guard.validate_port(65535) is True
        assert tor_guard.validate_port(0) is False
        assert tor_guard.validate_port(65536) is False
        assert tor_guard.validate_port(-1) is False

    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        cfg = {
            "SOCKS_PORTS": [9050, 9150],
            "CHECK_HOSTS": ["127.0.0.1"],
            "GRACE_SECONDS": 8,
            "RETRIES": 2,
            "CHECK_INTERVAL": 3,
            "RED_IMAGE_PATH": "",
        }

        assert tor_guard.validate_config(cfg) is True

    def test_validate_invalid_port(self):
        """Test validation fails for invalid ports."""
        cfg = {
            "SOCKS_PORTS": [9050, 99999],  # Invalid port
            "CHECK_HOSTS": ["127.0.0.1"],
            "GRACE_SECONDS": 8,
            "RETRIES": 2,
            "CHECK_INTERVAL": 3,
            "RED_IMAGE_PATH": "",
        }

        assert tor_guard.validate_config(cfg) is False

    def test_validate_negative_grace_seconds(self):
        """Test validation fails for negative grace seconds."""
        cfg = {
            "SOCKS_PORTS": [9050],
            "CHECK_HOSTS": ["127.0.0.1"],
            "GRACE_SECONDS": -1,  # Invalid
            "RETRIES": 2,
            "CHECK_INTERVAL": 3,
            "RED_IMAGE_PATH": "",
        }

        assert tor_guard.validate_config(cfg) is False

    def test_validate_zero_retries(self):
        """Test validation fails for zero retries."""
        cfg = {
            "SOCKS_PORTS": [9050],
            "CHECK_HOSTS": ["127.0.0.1"],
            "GRACE_SECONDS": 8,
            "RETRIES": 0,  # Invalid
            "CHECK_INTERVAL": 3,
            "RED_IMAGE_PATH": "",
        }

        assert tor_guard.validate_config(cfg) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
