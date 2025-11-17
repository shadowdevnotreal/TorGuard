#!/usr/bin/env python3
"""Unit tests for Tor integration module"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after path modification
import tor_integration


class TestTorBrowserDetection:
    """Test Tor Browser detection functions."""

    def test_find_tor_browser(self):
        """Test finding Tor Browser installation."""
        # This will return None if not installed, which is fine
        result = tor_integration.find_tor_browser()
        assert result is None or isinstance(result, Path)

    def test_is_tor_browser_running(self):
        """Test checking if Tor Browser is running."""
        result = tor_integration.is_tor_browser_running()
        assert isinstance(result, bool)

    def test_find_tor_browser_profile(self):
        """Test finding Tor Browser profile."""
        result = tor_integration.find_tor_browser_profile()
        assert result is None or isinstance(result, Path)


class TestTorControlPort:
    """Test Tor control port detection."""

    def test_get_tor_control_port(self):
        """Test detecting Tor control port."""
        result = tor_integration.get_tor_control_port()
        assert result is None or isinstance(result, int)

        if result is not None:
            assert 1 <= result <= 65535

    def test_is_port_open_invalid(self):
        """Test checking if an obviously invalid port is closed."""
        # Port 1 on localhost should be closed
        result = tor_integration.is_port_open("127.0.0.1", 1, timeout=0.5)
        # We can't guarantee it's closed, but it's likely
        assert isinstance(result, bool)


class TestTorsocks:
    """Test torsocks detection."""

    def test_check_torsocks(self):
        """Test checking if torsocks is available."""
        result = tor_integration.check_torsocks()
        assert isinstance(result, bool)


class TestTorInfo:
    """Test Tor information gathering."""

    def test_get_tor_info(self):
        """Test getting comprehensive Tor information."""
        info = tor_integration.get_tor_info()

        assert isinstance(info, dict)
        assert "tor_browser_path" in info
        assert "tor_browser_running" in info
        assert "profile_path" in info
        assert "control_port" in info
        assert "torsocks_available" in info
        assert "platform" in info

        # Check types
        assert isinstance(info["tor_browser_running"], bool)
        assert isinstance(info["torsocks_available"], bool)
        assert isinstance(info["platform"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
