#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tor_guard.py — interactive Tor monitor with curses menu, tkinter red-screen fallback, and config file.

Features:
- Curses menu: Start/Stop monitor, Status, Tail logs, Test Warning, Edit/View config, Quit
- Config file: /etc/tor_guard.conf (system) -> ~/.config/tor_guard/tor_guard.conf (user fallback)
- Tkinter fallback: full-screen red prompt; ASCII fallback if no GUI
- Safe net-kill: nmcli networking off OR ip link set <iface> down (with explicit consent by default)
- Robust Tor detection: SOCKS ports + tor process; grace+retries to avoid flapping

Run:
  sudo python3 tor_guard.py
"""

import argparse
import curses
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

# -------------- Defaults & constants --------------
DEFAULT_CFG = """
# tor_guard.conf
# Lines starting with '#' are comments. Key=Value format. Lists are comma-separated.

# Ports to probe for local Tor SOCKS
SOCKS_PORTS=9050,9150

# Hosts to probe (localhost v4/v6)
CHECK_HOSTS=127.0.0.1,::1

# Seconds to wait before treating 1 failure as 'real'
GRACE_SECONDS=8

# Consecutive failed checks required to trigger action
RETRIES=2

# Probe interval in seconds
CHECK_INTERVAL=3

# Require explicit YES before disabling networking (recommended)
REQUIRE_CONFIRM=true

# Prefer tkinter GUI full-screen warning when available
USE_TK=true

# Prefer curses for menu (headless-safe; will fallback automatically)
USE_CURSES=true

# Optional path to a red image (not required). If set and running X, we try to show it via 'display' or 'feh'.
RED_IMAGE_PATH=

# Optional whitelist of interfaces to consider for 'ip link set <iface> down' (comma-separated).
# Leave empty to auto-pick the first non-loopback UP interface.
INTERFACE_WHITELIST=
""".lstrip()

APP_NAME = "TorGuard"
LOGFILE = "/var/tmp/tor_guard.log"
SOCKET_TIMEOUT = 1.0
LOG_TAIL_LINES = 30
SUBPROCESS_TIMEOUT = 5

# Platform detection
SYSTEM = platform.system().lower()  # 'linux', 'darwin' (macOS), 'windows'
IS_LINUX = SYSTEM == "linux"
IS_MACOS = SYSTEM == "darwin"
IS_WINDOWS = SYSTEM == "windows"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGFILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(APP_NAME)


# -------------- Config handling --------------
def cfg_paths() -> tuple[Path, Path]:
    """Return system and user config file paths."""
    sys_cfg = Path("/etc/tor_guard.conf")
    usr_cfg = Path.home() / ".config" / "tor_guard" / "tor_guard.conf"
    return sys_cfg, usr_cfg


def ensure_user_cfg() -> Path:
    """Ensure a config file exists, creating user config if needed."""
    sys_cfg, usr_cfg = cfg_paths()
    if not sys_cfg.exists() and not usr_cfg.exists():
        try:
            usr_cfg.parent.mkdir(parents=True, exist_ok=True)
            usr_cfg.write_text(DEFAULT_CFG)
            logger.info(f"Created default config at {usr_cfg}")
        except (OSError, IOError) as e:
            logger.error(f"Failed to create config file: {e}")
            raise
    return sys_cfg if sys_cfg.exists() else usr_cfg


def validate_port(port: int) -> bool:
    """Validate port number is in valid range."""
    return 1 <= port <= 65535


def validate_config(cfg: Dict[str, Any]) -> bool:
    """Validate configuration values."""
    try:
        # Validate ports
        for port in cfg["SOCKS_PORTS"]:
            if not validate_port(port):
                logger.error(f"Invalid port number: {port}")
                return False

        # Validate hosts
        if not cfg["CHECK_HOSTS"]:
            logger.error("CHECK_HOSTS cannot be empty")
            return False

        # Validate numeric values
        if cfg["GRACE_SECONDS"] < 0:
            logger.error(f"GRACE_SECONDS cannot be negative: {cfg['GRACE_SECONDS']}")
            return False
        if cfg["RETRIES"] < 1:
            logger.error(f"RETRIES must be at least 1: {cfg['RETRIES']}")
            return False
        if cfg["CHECK_INTERVAL"] < 1:
            logger.error(f"CHECK_INTERVAL must be at least 1: {cfg['CHECK_INTERVAL']}")
            return False

        # Validate file paths
        if cfg["RED_IMAGE_PATH"]:
            path = Path(os.path.expanduser(cfg["RED_IMAGE_PATH"]))
            if not path.exists():
                logger.warning(f"RED_IMAGE_PATH does not exist: {path}")

        return True
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Configuration validation error: {e}")
        return False


def parse_cfg(p: Path) -> Dict[str, Any]:
    """Parse configuration file and return config dictionary."""
    cfg: Dict[str, Any] = {
        "SOCKS_PORTS": [9050, 9150],
        "CHECK_HOSTS": ["127.0.0.1", "::1"],
        "GRACE_SECONDS": 8,
        "RETRIES": 2,
        "CHECK_INTERVAL": 3,
        "REQUIRE_CONFIRM": True,
        "USE_TK": True,
        "USE_CURSES": True,
        "RED_IMAGE_PATH": "",
        "INTERFACE_WHITELIST": [],
    }

    try:
        raw = p.read_text().splitlines()
    except (OSError, IOError) as e:
        logger.error(f"Failed to read config file {p}: {e}")
        return cfg

    def to_bool(v: str) -> bool:
        return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

    for line in raw:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        try:
            k, v = [x.strip() for x in line.split("=", 1)]
            if k == "SOCKS_PORTS":
                cfg[k] = [int(x) for x in v.split(",") if x.strip()]
            elif k == "CHECK_HOSTS":
                cfg[k] = [x.strip() for x in v.split(",") if x.strip()]
            elif k in ("GRACE_SECONDS", "RETRIES", "CHECK_INTERVAL"):
                cfg[k] = int(v)
            elif k == "REQUIRE_CONFIRM":
                cfg[k] = to_bool(v)
            elif k == "USE_TK":
                cfg[k] = to_bool(v)
            elif k == "USE_CURSES":
                cfg[k] = to_bool(v)
            elif k == "RED_IMAGE_PATH":
                cfg[k] = v.strip()
            elif k == "INTERFACE_WHITELIST":
                cfg[k] = [x.strip() for x in v.split(",") if x.strip()]
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse config line '{line}': {e}")
            continue

    return cfg


# -------------- Dependency checks --------------
def check_dependencies() -> Dict[str, bool]:
    """Check if required system dependencies are available."""
    deps = {
        "ip": shutil.which("ip") is not None,
        "pgrep": shutil.which("pgrep") is not None,
        "nmcli": shutil.which("nmcli") is not None,
    }

    missing = [name for name, available in deps.items() if not available and name != "nmcli"]
    if missing:
        logger.error(f"Missing required dependencies: {', '.join(missing)}")
        logger.error("Please install: iproute2, procps")

    if not deps["nmcli"]:
        logger.warning("NetworkManager (nmcli) not found. Will use 'ip' commands for network control.")

    return deps


# -------------- Tor checks --------------
def socks_alive(cfg: Dict[str, Any]) -> bool:
    """Check if Tor SOCKS proxy is responding."""
    for host in cfg["CHECK_HOSTS"]:
        for port in cfg["SOCKS_PORTS"]:
            try:
                family = socket.AF_INET6 if ":" in host else socket.AF_INET
                with socket.socket(family, socket.SOCK_STREAM) as s:
                    s.settimeout(SOCKET_TIMEOUT)
                    s.connect((host, port))
                    logger.debug(f"SOCKS connection successful: {host}:{port}")
                    return True
            except (socket.timeout, socket.error, OSError) as e:
                logger.debug(f"SOCKS connection failed {host}:{port}: {e}")
                continue
    return False


def have_tor_process() -> bool:
    """Check if tor process is running (exact match)."""
    try:
        # Use -x for exact match to avoid false positives
        out = subprocess.check_output(
            ["pgrep", "-x", "tor"],
            stderr=subprocess.DEVNULL,
            timeout=SUBPROCESS_TIMEOUT
        )
        result = bool(out.strip())
        logger.debug(f"Tor process check: {result}")
        return result
    except subprocess.CalledProcessError:
        logger.debug("Tor process not found")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("Tor process check timed out")
        return False
    except FileNotFoundError:
        logger.error("pgrep command not found")
        return False


# -------------- Net control --------------
def detect_network_manager() -> bool:
    """Check if NetworkManager is available."""
    return shutil.which("nmcli") is not None


def list_up_ifaces() -> List[str]:
    """List all UP network interfaces (excluding loopback)."""
    if IS_LINUX:
        return list_up_ifaces_linux()
    elif IS_MACOS:
        return list_up_ifaces_macos()
    elif IS_WINDOWS:
        return list_up_ifaces_windows()
    return []


def list_up_ifaces_linux() -> List[str]:
    """List all UP network interfaces on Linux."""
    try:
        out = subprocess.check_output(
            ["ip", "-o", "link", "show", "up"],
            timeout=SUBPROCESS_TIMEOUT
        ).decode()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Failed to list network interfaces: {e}")
        return []

    names = []
    for line in out.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 2:
            name = parts[1].strip()
            if name != "lo":
                names.append(name)

    logger.debug(f"Found UP interfaces (Linux): {names}")
    return names


def list_up_ifaces_macos() -> List[str]:
    """List all UP network interfaces on macOS."""
    try:
        out = subprocess.check_output(
            ["networksetup", "-listallhardwareports"],
            timeout=SUBPROCESS_TIMEOUT
        ).decode()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Failed to list network interfaces on macOS: {e}")
        return []

    # Parse networksetup output
    names = []
    lines = out.strip().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("Device:"):
            device = line.split(":")[1].strip()
            # Check if interface is up
            try:
                status_out = subprocess.check_output(
                    ["ifconfig", device],
                    stderr=subprocess.DEVNULL,
                    timeout=SUBPROCESS_TIMEOUT
                ).decode()
                if "status: active" in status_out.lower() or "inet" in status_out:
                    if device not in ["lo0", "lo"]:
                        names.append(device)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                continue

    logger.debug(f"Found UP interfaces (macOS): {names}")
    return names


def list_up_ifaces_windows() -> List[str]:
    """List all UP network interfaces on Windows."""
    try:
        out = subprocess.check_output(
            ["netsh", "interface", "show", "interface"],
            timeout=SUBPROCESS_TIMEOUT
        ).decode()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Failed to list network interfaces on Windows: {e}")
        return []

    names = []
    for line in out.strip().splitlines()[3:]:  # Skip header lines
        parts = line.split()
        if len(parts) >= 4 and parts[2].lower() == "connected":
            # Interface name is the last part
            name = " ".join(parts[3:])
            if "loopback" not in name.lower():
                names.append(name)

    logger.debug(f"Found UP interfaces (Windows): {names}")
    return names


def choose_iface(cfg: Dict[str, Any]) -> Optional[str]:
    """Choose appropriate network interface to disable."""
    wl = cfg["INTERFACE_WHITELIST"]
    up = list_up_ifaces()

    if wl:
        for n in up:
            if n in wl:
                logger.info(f"Selected whitelisted interface: {n}")
                return n
        logger.warning(f"No whitelisted interfaces found. Whitelist: {wl}, Available: {up}")
        return None

    if up:
        logger.info(f"Selected interface: {up[0]} (from available: {up})")
        return up[0]

    logger.error("No suitable interfaces found")
    return None


def bring_down_network(cfg: Dict[str, Any]) -> bool:
    """Disable network connectivity (platform-aware)."""
    logger.info("User requested network disable")

    if IS_LINUX:
        return bring_down_network_linux(cfg)
    elif IS_MACOS:
        return bring_down_network_macos(cfg)
    elif IS_WINDOWS:
        return bring_down_network_windows(cfg)
    else:
        logger.error(f"Unsupported platform: {SYSTEM}")
        print(f"Error: Network disable not supported on {SYSTEM}")
        return False


def bring_down_network_linux(cfg: Dict[str, Any]) -> bool:
    """Disable network on Linux."""
    if detect_network_manager():
        print("\nRunning: nmcli networking off")
        if cfg["REQUIRE_CONFIRM"]:
            ok = input("Type YES to proceed: ").strip()
            if ok != "YES":
                print("Aborted.")
                logger.info("User aborted network disable")
                return False

        try:
            rc = subprocess.call(
                ["nmcli", "networking", "off"],
                timeout=SUBPROCESS_TIMEOUT
            )
            logger.info(f"nmcli networking off rc={rc}")
            return rc == 0
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Failed to disable networking via nmcli: {e}")
            return False

    iface = choose_iface(cfg)
    if not iface:
        print("No suitable interface found (excluding loopback).")
        logger.error("Cannot disable network: no suitable interface")
        return False

    print(f"\nAbout to run: ip link set {iface} down")
    if cfg["REQUIRE_CONFIRM"]:
        ok = input("Type YES to proceed: ").strip()
        if ok != "YES":
            print("Aborted.")
            logger.info("User aborted network disable")
            return False

    try:
        rc = subprocess.call(
            ["ip", "link", "set", iface, "down"],
            timeout=SUBPROCESS_TIMEOUT
        )
        logger.info(f"ip link set {iface} down rc={rc}")
        return rc == 0
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Failed to disable interface {iface}: {e}")
        return False


def bring_down_network_macos(cfg: Dict[str, Any]) -> bool:
    """Disable network on macOS using networksetup."""
    # Get list of network services
    try:
        out = subprocess.check_output(
            ["networksetup", "-listallnetworkservices"],
            timeout=SUBPROCESS_TIMEOUT
        ).decode()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Failed to list network services on macOS: {e}")
        return False

    services = [line.strip() for line in out.strip().splitlines()[1:] if line.strip() and not line.startswith("*")]

    if not services:
        print("No network services found.")
        logger.error("No network services found on macOS")
        return False

    print(f"\nFound network services: {', '.join(services)}")
    print("Will disable all network services")

    if cfg["REQUIRE_CONFIRM"]:
        ok = input("Type YES to proceed: ").strip()
        if ok != "YES":
            print("Aborted.")
            logger.info("User aborted network disable")
            return False

    success = True
    for service in services:
        try:
            rc = subprocess.call(
                ["networksetup", "-setnetworkserviceenabled", service, "off"],
                timeout=SUBPROCESS_TIMEOUT
            )
            logger.info(f"Disabled service '{service}' rc={rc}")
            if rc != 0:
                success = False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Failed to disable service '{service}': {e}")
            success = False

    return success


def bring_down_network_windows(cfg: Dict[str, Any]) -> bool:
    """Disable network on Windows using netsh."""
    ifaces = list_up_ifaces()

    if not ifaces:
        print("No network interfaces found.")
        logger.error("No network interfaces found on Windows")
        return False

    print(f"\nFound network interfaces: {', '.join(ifaces)}")
    print("Will disable all network interfaces")

    if cfg["REQUIRE_CONFIRM"]:
        ok = input("Type YES to proceed: ").strip()
        if ok != "YES":
            print("Aborted.")
            logger.info("User aborted network disable")
            return False

    success = True
    for iface in ifaces:
        try:
            rc = subprocess.call(
                ["netsh", "interface", "set", "interface", iface, "admin=disable"],
                timeout=SUBPROCESS_TIMEOUT
            )
            logger.info(f"Disabled interface '{iface}' rc={rc}")
            if rc != 0:
                success = False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Failed to disable interface '{iface}': {e}")
            success = False

    return success


def print_reenable_instructions() -> None:
    """Print instructions for manually re-enabling network (platform-aware)."""
    print("\nManual re-enable instructions:")

    if IS_LINUX:
        if detect_network_manager():
            print(" - NetworkManager:  sudo nmcli networking on")
        print(" - Generic Linux:   sudo ip link set <iface> up")
        print(" - Debian ifup:     sudo ifup <iface>")
    elif IS_MACOS:
        print(" - macOS:           sudo networksetup -setnetworkserviceenabled \"Wi-Fi\" on")
        print(" - Or:              sudo ifconfig en0 up")
        print(" - List services:   networksetup -listallnetworkservices")
    elif IS_WINDOWS:
        print(" - Windows:         netsh interface set interface \"<name>\" admin=enable")
        print(" - List interfaces: netsh interface show interface")
        print(" - Or use Network Settings GUI")

    print("\nThen restart your browser.\n")


# -------------- Warning UIs --------------
def show_red_image_if_possible(cfg: Dict[str, Any]) -> bool:
    """Display warning image if configured and possible."""
    img = cfg.get("RED_IMAGE_PATH") or ""
    if not img:
        return False

    img_path = os.path.expanduser(img)
    if not os.path.exists(img_path):
        logger.warning(f"RED_IMAGE_PATH does not exist: {img_path}")
        return False

    # try ImageMagick 'display' or 'feh'
    for viewer in ("display", "feh"):
        if shutil.which(viewer):
            try:
                # best effort full-screen
                subprocess.Popen([viewer, "-F", img_path])
                logger.info(f"Displayed warning image using {viewer}")
                return True
            except (OSError, subprocess.SubprocessError) as e:
                logger.warning(f"Failed to display image with {viewer}: {e}")
                continue

    logger.warning("No image viewer available (tried display, feh)")
    return False


def tk_fullscreen_warning() -> bool:
    """Display full-screen warning using Tkinter."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.title("TOR CONNECTION LOST")
        root.attributes("-fullscreen", True)
        root.configure(bg="red")
        msg = ("TOR CONNECTION LOST\n\n"
               "Close your browser NOW.\n"
               "After closing the browser, you may proceed to disable networking.\n\n"
               "Press the button below once you've closed your browser.")
        label = tk.Label(
            root,
            text=msg,
            bg="red",
            fg="white",
            font=("Helvetica", 24, "bold"),
            justify="center"
        )
        label.pack(expand=True, fill="both", padx=40, pady=40)
        btn = tk.Button(
            root,
            text="I have closed my browser",
            font=("Helvetica", 18, "bold"),
            command=root.destroy
        )
        btn.pack(pady=40)
        root.mainloop()
        logger.info("Tkinter warning displayed and dismissed")
        return True
    except (ImportError, tk.TclError) as e:
        logger.warning(f"Tkinter warning failed: {e}")
        return False


def ascii_red_box() -> None:
    """Display ASCII warning in terminal."""
    print("\n" + "=" * 80)
    print("!!!  TOR CONNECTION LOST  !!!".center(80))
    print("CLOSE YOUR BROWSER NOW".center(80))
    print("=" * 80 + "\n")
    input("Press Enter after you've closed your browser...")
    logger.info("ASCII warning displayed and dismissed")


def show_fullscreen_warning(cfg: Dict[str, Any]) -> None:
    """Display warning using best available method."""
    used = False

    # Optional: show image overlay if configured
    used = show_red_image_if_possible(cfg)

    # Tk fallback (stays top until dismissed)
    if not used and cfg["USE_TK"]:
        used = tk_fullscreen_warning()

    if not used:
        ascii_red_box()


# -------------- Monitor thread --------------
class Monitor(threading.Thread):
    """Background thread that monitors Tor connectivity."""

    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(daemon=True)
        self.cfg = cfg
        self._stop = threading.Event()
        self._state: Optional[bool] = None
        self._state_lock = threading.Lock()

    @property
    def state(self) -> Optional[bool]:
        """Thread-safe state getter."""
        with self._state_lock:
            return self._state

    @state.setter
    def state(self, value: Optional[bool]) -> None:
        """Thread-safe state setter."""
        with self._state_lock:
            self._state = value

    def stop(self) -> None:
        """Signal the monitor thread to stop."""
        self._stop.set()
        logger.info("Monitor stop requested")

    def run(self) -> None:
        """Main monitoring loop."""
        logger.info("Monitor started")

        while not self._stop.is_set():
            alive = socks_alive(self.cfg) or have_tor_process()

            if alive:
                if self.state is False:
                    logger.info("Tor restored")
                self.state = True
                time.sleep(self.cfg["CHECK_INTERVAL"])
                continue

            # Tor down path
            logger.warning("Tor appears down; grace+retries begin")
            ok = False

            for attempt in range(self.cfg["RETRIES"]):
                time.sleep(self.cfg["GRACE_SECONDS"])
                if self._stop.is_set():
                    return

                if socks_alive(self.cfg) or have_tor_process():
                    ok = True
                    logger.info(f"Tor recovered on retry {attempt + 1}")
                    break

            if ok:
                logger.info("Short outage recovered")
                self.state = True
                continue

            # Persistent outage -> alert & potentially disable
            logger.error("Persistent Tor outage detected -> triggering warning")
            show_fullscreen_warning(self.cfg)

            if self._stop.is_set():
                return

            resp = input("Proceed to disable network now? Type YES to proceed: ").strip()
            if resp == "YES":
                if os.geteuid() != 0:
                    print("Must be root to disable networking. Re-run with sudo.")
                    logger.error("Abort: not root")
                else:
                    success = bring_down_network(self.cfg)
                    if success:
                        print("Network disabled.")
                        print_reenable_instructions()
                        logger.critical("Network disabled by tool; exiting monitor")
                        # Exit gracefully
                        sys.exit(0)
            else:
                print("User aborted network disable; continuing monitor.")
                logger.info("User aborted network disable after warning")
                self.state = False
                time.sleep(self.cfg["CHECK_INTERVAL"])


# -------------- Curses menu --------------
class MenuApp:
    """Interactive curses-based menu application."""

    ITEMS = [
        "Start Monitor",
        "Stop Monitor",
        "Status",
        "Tail Logs",
        "Test Warning",
        "Show Config Path",
        "Quit",
    ]

    def __init__(self, cfg_path: Path, cfg: Dict[str, Any]):
        self.cfg_path = cfg_path
        self.cfg = cfg
        self.mon: Optional[Monitor] = None
        self.idx = 0

    def start_monitor(self) -> str:
        """Start the monitoring thread."""
        if self.mon and self.mon.is_alive():
            return "Monitor already running."

        self.mon = Monitor(self.cfg)
        self.mon.start()
        logger.info("Monitor started from menu")
        return "Monitor started."

    def stop_monitor(self) -> str:
        """Stop the monitoring thread."""
        if self.mon and self.mon.is_alive():
            self.mon.stop()
            logger.info("Monitor stopped from menu")
            return "Stopping monitor…"
        return "Monitor not running."

    def status(self) -> str:
        """Get current monitor status."""
        if self.mon and self.mon.is_alive():
            s = self.mon.state
            state = "unknown" if s is None else ("Tor OK" if s else "Tor DOWN")
            return f"Monitor: RUNNING  |  State: {state}"
        else:
            return "Monitor: STOPPED"

    def tail_logs(self, lines: int = LOG_TAIL_LINES) -> str:
        """Get last N lines from log file."""
        try:
            with open(LOGFILE, "r") as f:
                data = f.readlines()[-lines:]
        except (OSError, IOError) as e:
            logger.error(f"Failed to read log file: {e}")
            data = [f"<error reading logs: {e}>"]

        return "".join(data) if data else "<no logs yet>"

    def test_warning(self) -> str:
        """Test the warning display system."""
        show_fullscreen_warning(self.cfg)
        return "Test warning closed."

    def show_cfg_path(self) -> str:
        """Show the configuration file path."""
        return f"Using config: {self.cfg_path}\n(Edit with sudo if system path.)"

    def run(self, stdscr) -> None:
        """Main curses UI loop."""
        curses.curs_set(0)
        msg = ""

        while True:
            try:
                h, w = stdscr.getmaxyx()
                stdscr.clear()

                title = f"{APP_NAME} — Tor Monitor"
                stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)

                for i, item in enumerate(self.ITEMS):
                    attr = curses.A_REVERSE if i == self.idx else curses.A_NORMAL
                    stdscr.addstr(2 + i, 4, item.ljust(20), attr)

                # footer / messages
                if msg:
                    wrapped = textwrap.wrap(msg, width=w - 8)
                    for i, line in enumerate(wrapped):
                        stdscr.addstr(h - 3 - (len(wrapped) - 1 - i), 4, line)

                stdscr.refresh()
                ch = stdscr.getch()

                if ch in (curses.KEY_UP, ord('k')):
                    self.idx = (self.idx - 1) % len(self.ITEMS)
                elif ch in (curses.KEY_DOWN, ord('j')):
                    self.idx = (self.idx + 1) % len(self.ITEMS)
                elif ch in (curses.KEY_ENTER, 10, 13):
                    msg = self._handle_selection(stdscr)
                    if msg == "QUIT":
                        break
                elif ch in (ord('q'), 27):  # q or ESC
                    self._cleanup_and_exit()
                    break

            except curses.error as e:
                logger.error(f"Curses error: {e}")
                break

    def _handle_selection(self, stdscr) -> str:
        """Handle menu item selection."""
        sel = self.ITEMS[self.idx]

        if sel == "Start Monitor":
            return self.start_monitor()
        elif sel == "Stop Monitor":
            return self.stop_monitor()
        elif sel == "Status":
            return self.status()
        elif sel == "Tail Logs":
            return self._show_logs()
        elif sel == "Test Warning":
            return self._test_warning()
        elif sel == "Show Config Path":
            return self.show_cfg_path()
        elif sel == "Quit":
            self._cleanup_and_exit()
            return "QUIT"

        return ""

    def _show_logs(self) -> str:
        """Display logs in a separate screen."""
        curses.endwin()
        print("\n--- LOG TAIL ---")
        print(self.tail_logs())
        input("\nPress Enter to return to menu...")
        return "Logs displayed."

    def _test_warning(self) -> str:
        """Test warning display."""
        curses.endwin()
        result = self.test_warning()
        return result

    def _cleanup_and_exit(self) -> None:
        """Clean up resources before exit."""
        if self.mon and self.mon.is_alive():
            self.mon.stop()
            self.mon.join(timeout=1.0)
        logger.info("Application exiting")


# -------------- Entry point --------------
def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="TorGuard - Monitor Tor connectivity and protect against leaks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo python3 tor_guard.py              # Run with menu interface
  sudo python3 tor_guard.py --no-menu    # Run in headless mode
  sudo python3 tor_guard.py --debug      # Enable debug logging
  python3 tor_guard.py --config-path     # Show config file location

Note: Requires sudo for network disable operations.
        """
    )

    parser.add_argument(
        "--no-menu",
        action="store_true",
        help="Run without curses menu (headless mode)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--config-path",
        action="store_true",
        help="Show config file path and exit"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Use specific config file"
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_arguments()

    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    # Get config file
    try:
        if args.config:
            cfg_file = args.config
            if not cfg_file.exists():
                print(f"Error: Config file not found: {cfg_file}")
                sys.exit(1)
        else:
            cfg_file = ensure_user_cfg()
    except (OSError, IOError) as e:
        print(f"Error: Failed to access config file: {e}")
        sys.exit(1)

    # Show config path if requested
    if args.config_path:
        print(f"Config file: {cfg_file}")
        sys.exit(0)

    # Parse and validate config
    cfg = parse_cfg(cfg_file)
    if not validate_config(cfg):
        print("Error: Invalid configuration. Check logs for details.")
        sys.exit(1)

    logger.info(f"Using config file: {cfg_file}")

    # Check dependencies
    deps = check_dependencies()
    if not deps["ip"] or not deps["pgrep"]:
        print("Error: Missing required dependencies. Check logs for details.")
        sys.exit(1)

    # Check root privileges
    if os.geteuid() != 0:
        print("Note: run with sudo to allow network disable operations.\n")
        logger.warning("Not running as root - network disable will not work")

    # Decide on UI mode
    use_menu = not args.no_menu and cfg["USE_CURSES"]

    if not use_menu:
        # Headless mode
        print(f"{APP_NAME} running without menu. Ctrl-C to stop.")
        logger.info("Running in headless mode")
        mon = Monitor(cfg)
        mon.start()
        try:
            while mon.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            mon.stop()
            mon.join(timeout=2.0)
        return

    # Menu mode
    try:
        logger.info("Starting curses menu interface")
        curses.wrapper(MenuApp(cfg_file, cfg).run)
    except Exception as e:
        logger.error(f"Curses failed: {e}", exc_info=True)
        print(f"Curses failed; falling back to headless mode: {e}")
        mon = Monitor(cfg)
        mon.start()
        try:
            while mon.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            mon.stop()
            mon.join(timeout=2.0)


if __name__ == "__main__":
    main()
