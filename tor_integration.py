#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tor Integration Module - Helper functions for integrating with Tor Browser and other Tor tools

Features:
- Detect Tor Browser installation
- Check Tor Browser process
- Find Tor Browser profile directory
- Integration with torsocks
- Control port detection
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, List, Dict
import logging

logger = logging.getLogger("TorIntegration")

# Platform detection
SYSTEM = platform.system().lower()
IS_LINUX = SYSTEM == "linux"
IS_MACOS = SYSTEM == "darwin"
IS_WINDOWS = SYSTEM == "windows"


def find_tor_browser() -> Optional[Path]:
    """Find Tor Browser installation path."""
    search_paths: List[Path] = []

    if IS_LINUX:
        search_paths = [
            Path.home() / "tor-browser_en-US",
            Path.home() / "tor-browser",
            Path.home() / ".local" / "share" / "torbrowser",
            Path("/opt/torbrowser"),
            Path("/opt/tor-browser_en-US"),
        ]
    elif IS_MACOS:
        search_paths = [
            Path("/Applications/Tor Browser.app"),
            Path.home() / "Applications" / "Tor Browser.app",
        ]
    elif IS_WINDOWS:
        search_paths = [
            Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Tor Browser",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Tor Browser",
            Path.home() / "Desktop" / "Tor Browser",
        ]

    for path in search_paths:
        if path.exists():
            logger.info(f"Found Tor Browser at: {path}")
            return path

    logger.warning("Tor Browser installation not found")
    return None


def is_tor_browser_running() -> bool:
    """Check if Tor Browser is currently running."""
    try:
        if IS_LINUX or IS_MACOS:
            # Check for firefox process with tor profile
            result = subprocess.run(
                ["pgrep", "-f", "firefox.*tor"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        elif IS_WINDOWS:
            # Check for firefox.exe in Tor Browser directory
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq firefox.exe"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "firefox.exe" in result.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Failed to check if Tor Browser is running: {e}")

    return False


def find_tor_browser_profile() -> Optional[Path]:
    """Find Tor Browser profile directory."""
    profile_paths: List[Path] = []

    if IS_LINUX or IS_MACOS:
        tb_path = find_tor_browser()
        if tb_path:
            profile_paths.append(tb_path / "Browser" / "TorBrowser" / "Data" / "Browser" / "profile.default")

    elif IS_WINDOWS:
        tb_path = find_tor_browser()
        if tb_path:
            profile_paths.append(tb_path / "Browser" / "TorBrowser" / "Data" / "Browser" / "profile.default")

    for path in profile_paths:
        if path.exists():
            logger.info(f"Found Tor Browser profile at: {path}")
            return path

    logger.warning("Tor Browser profile not found")
    return None


def get_tor_control_port() -> Optional[int]:
    """Detect Tor control port by checking common locations."""
    # Common control ports
    common_ports = [9051, 9151]

    # Try to read from torrc file
    torrc_paths: List[Path] = []

    if IS_LINUX:
        torrc_paths = [
            Path("/etc/tor/torrc"),
            Path.home() / ".tor" / "torrc",
        ]
    elif IS_MACOS:
        torrc_paths = [
            Path("/usr/local/etc/tor/torrc"),
            Path.home() / ".tor" / "torrc",
        ]
    elif IS_WINDOWS:
        torrc_paths = [
            Path(os.environ.get("APPDATA", "")) / "tor" / "torrc",
        ]

    # Add Tor Browser torrc
    tb_path = find_tor_browser()
    if tb_path:
        if IS_LINUX or IS_MACOS:
            torrc_paths.append(tb_path / "Browser" / "TorBrowser" / "Data" / "Tor" / "torrc")
        elif IS_WINDOWS:
            torrc_paths.append(tb_path / "Browser" / "TorBrowser" / "Data" / "Tor" / "torrc")

    # Try to find ControlPort in torrc files
    for torrc_path in torrc_paths:
        if torrc_path.exists():
            try:
                with open(torrc_path, 'r') as f:
                    for line in f:
                        if line.strip().startswith("ControlPort"):
                            parts = line.split()
                            if len(parts) >= 2:
                                try:
                                    port = int(parts[1])
                                    logger.info(f"Found ControlPort {port} in {torrc_path}")
                                    return port
                                except ValueError:
                                    continue
            except Exception as e:
                logger.debug(f"Could not read {torrc_path}: {e}")

    # Try common ports
    for port in common_ports:
        if is_port_open("127.0.0.1", port):
            logger.info(f"Found open control port: {port}")
            return port

    logger.warning("Could not detect Tor control port")
    return None


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a port is open."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except socket.error:
        return False


def check_torsocks() -> bool:
    """Check if torsocks is installed."""
    try:
        result = subprocess.run(
            ["which", "torsocks"] if not IS_WINDOWS else ["where", "torsocks"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_tor_info() -> Dict[str, any]:
    """Get comprehensive information about Tor installation."""
    info = {
        "tor_browser_path": find_tor_browser(),
        "tor_browser_running": is_tor_browser_running(),
        "profile_path": find_tor_browser_profile(),
        "control_port": get_tor_control_port(),
        "torsocks_available": check_torsocks(),
        "platform": SYSTEM,
    }

    return info


def print_tor_info() -> None:
    """Print Tor installation information."""
    print("=" * 60)
    print("Tor Integration Information")
    print("=" * 60)

    info = get_tor_info()

    print(f"Platform: {info['platform'].capitalize()}")
    print(f"\nTor Browser:")
    print(f"  Installation: {info['tor_browser_path'] or 'Not found'}")
    print(f"  Running: {'Yes' if info['tor_browser_running'] else 'No'}")
    print(f"  Profile: {info['profile_path'] or 'Not found'}")

    print(f"\nTor Service:")
    print(f"  Control Port: {info['control_port'] or 'Not detected'}")

    print(f"\nIntegration Tools:")
    print(f"  torsocks: {'Available' if info['torsocks_available'] else 'Not installed'}")

    print("=" * 60)


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Print Tor info when run directly
    print_tor_info()
