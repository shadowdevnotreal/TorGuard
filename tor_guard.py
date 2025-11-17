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

import os, sys, time, socket, subprocess, threading, shutil, curses, textwrap
from pathlib import Path

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

APP = "TorGuard"
LOGFILE = "/var/tmp/tor_guard.log"

# -------------- Config handling --------------
def cfg_paths():
    sys_cfg = Path("/etc/tor_guard.conf")
    usr_cfg = Path.home() / ".config" / "tor_guard" / "tor_guard.conf"
    return sys_cfg, usr_cfg

def ensure_user_cfg():
    sys_cfg, usr_cfg = cfg_paths()
    if not sys_cfg.exists() and not usr_cfg.exists():
        usr_cfg.parent.mkdir(parents=True, exist_ok=True)
        usr_cfg.write_text(DEFAULT_CFG)
    return sys_cfg if sys_cfg.exists() else usr_cfg

def parse_cfg(p: Path):
    cfg = {
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
    except Exception:
        return cfg
    def to_bool(v):
        return str(v).strip().lower() in ("1","true","yes","y","on")
    for line in raw:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = [x.strip() for x in line.split("=", 1)]
        if k == "SOCKS_PORTS":
            cfg[k] = [int(x) for x in v.split(",") if x.strip()]
        elif k == "CHECK_HOSTS":
            cfg[k] = [x.strip() for x in v.split(",") if x.strip()]
        elif k in ("GRACE_SECONDS","RETRIES","CHECK_INTERVAL"):
            try:
                cfg[k] = int(v)
            except ValueError:
                pass
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
    return cfg

# -------------- Logging --------------
def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOGFILE, "a") as f:
            f.write(f"{ts} {msg}\n")
    except Exception:
        pass

# -------------- Tor checks --------------
def socks_alive(cfg) -> bool:
    for host in cfg["CHECK_HOSTS"]:
        for port in cfg["SOCKS_PORTS"]:
            try:
                family = socket.AF_INET6 if ":" in host else socket.AF_INET
                with socket.socket(family, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    s.connect((host, port))
                    return True
            except Exception:
                continue
    return False

def have_tor_process() -> bool:
    try:
        out = subprocess.check_output(["pgrep", "-f", "tor"], stderr=subprocess.DEVNULL)
        return bool(out.strip())
    except subprocess.CalledProcessError:
        return False

# -------------- Net control --------------
def detect_network_manager() -> bool:
    return shutil.which("nmcli") is not None

def list_up_ifaces():
    try:
        out = subprocess.check_output(["ip", "-o", "link", "show", "up"]).decode()
    except Exception:
        return []
    names = []
    for line in out.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 2:
            name = parts[1].strip()
            if name != "lo":
                names.append(name)
    return names

def choose_iface(cfg):
    wl = cfg["INTERFACE_WHITELIST"]
    up = list_up_ifaces()
    if wl:
        for n in up:
            if n in wl:
                return n
        return None
    return up[0] if up else None

def bring_down_network(cfg) -> bool:
    log("User requested network disable.")
    if detect_network_manager():
        print("\nRunning: nmcli networking off")
        if cfg["REQUIRE_CONFIRM"]:
            ok = input("Type YES to proceed: ").strip()
            if ok != "YES":
                print("Aborted.")
                return False
        rc = subprocess.call(["nmcli", "networking", "off"])
        log(f"nmcli networking off rc={rc}")
        return rc == 0
    iface = choose_iface(cfg)
    if not iface:
        print("No suitable interface found (excluding loopback).")
        return False
    print(f"\nAbout to run: ip link set {iface} down")
    if cfg["REQUIRE_CONFIRM"]:
        ok = input("Type YES to proceed: ").strip()
        if ok != "YES":
            print("Aborted.")
            return False
    rc = subprocess.call(["ip", "link", "set", iface, "down"])
    log(f"ip link set {iface} down rc={rc}")
    return rc == 0

def print_reenable_instructions():
    print("\nManual re-enable instructions (choose one):")
    if detect_network_manager():
        print(" - NetworkManager:  sudo nmcli networking on")
    print(" - Generic Linux:   sudo ip link set <iface> up")
    print(" - Debian ifup:     sudo ifup <iface>")
    print(" - macOS examples:  sudo ifconfig en0 up   or   networksetup -setnetworkserviceenabled \"Wi-Fi\" on")
    print("Then restart your browser.\n")

# -------------- Warning UIs --------------
def show_red_image_if_possible(cfg) -> bool:
    img = cfg.get("RED_IMAGE_PATH") or ""
    if not img:
        return False
    img = os.path.expanduser(img)
    if not os.path.exists(img):
        return False
    # try ImageMagick 'display' or 'feh'
    for viewer in ("display", "feh"):
        if shutil.which(viewer):
            try:
                # best effort full-screen
                subprocess.Popen([viewer, "-F", img])
                return True
            except Exception:
                pass
    return False

def tk_fullscreen_warning():
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
        label = tk.Label(root, text=msg, bg="red", fg="white", font=("Helvetica", 24, "bold"), justify="center")
        label.pack(expand=True, fill="both", padx=40, pady=40)
        btn = tk.Button(root, text="I have closed my browser", font=("Helvetica", 18, "bold"), command=root.destroy)
        btn.pack(pady=40)
        root.mainloop()
        return True
    except Exception:
        return False

def ascii_red_box():
    print("\n" + "="*80)
    print("!!!  TOR CONNECTION LOST  !!!".center(80))
    print("CLOSE YOUR BROWSER NOW".center(80))
    print("="*80 + "\n")
    input("Press Enter after you've closed your browser...")

def show_fullscreen_warning(cfg):
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
    def __init__(self, cfg):
        super().__init__(daemon=True)
        self.cfg = cfg
        self._stop = threading.Event()
        self.state = None
    def stop(self):
        self._stop.set()
    def run(self):
        log("Monitor started")
        while not self._stop.is_set():
            alive = socks_alive(self.cfg) or have_tor_process()
            if alive:
                if self.state is False:
                    log("Tor restored")
                self.state = True
                time.sleep(self.cfg["CHECK_INTERVAL"])
                continue

            # Tor down path
            log("Tor appears down; grace+retries begin")
            ok = False
            for _ in range(self.cfg["RETRIES"]):
                time.sleep(self.cfg["GRACE_SECONDS"])
                if self._stop.is_set():
                    return
                if socks_alive(self.cfg) or have_tor_process():
                    ok = True
                    break
            if ok:
                log("Short outage recovered")
                self.state = True
                continue

            # Persistent outage -> alert & potentially disable
            log("Persistent outage -> warning")
            show_fullscreen_warning(self.cfg)
            if self._stop.is_set():
                return
            resp = input("Proceed to disable network now? Type YES to proceed: ").strip()
            if resp == "YES":
                if os.geteuid() != 0:
                    print("Must be root to disable networking. Re-run with sudo.")
                    log("Abort: not root")
                else:
                    success = bring_down_network(self.cfg)
                    if success:
                        print("Network disabled.")
                        print_reenable_instructions()
                        log("Network disabled by tool; exiting monitor.")
                        # Exit entirely; user will re-enable manually.
                        os._exit(0)
            else:
                print("User aborted network disable; continuing monitor.")
                log("User aborted network disable after warning.")
                self.state = False
                time.sleep(self.cfg["CHECK_INTERVAL"])

# -------------- Curses menu --------------
class MenuApp:
    ITEMS = [
        "Start Monitor",
        "Stop Monitor",
        "Status",
        "Tail Logs",
        "Test Warning",
        "Show Config Path",
        "Quit",
    ]
    def __init__(self, cfg_path, cfg):
        self.cfg_path = cfg_path
        self.cfg = cfg
        self.mon = None
        self.idx = 0

    def start_monitor(self):
        if self.mon and self.mon.is_alive():
            return "Monitor already running."
        self.mon = Monitor(self.cfg)
        self.mon.start()
        return "Monitor started."

    def stop_monitor(self):
        if self.mon and self.mon.is_alive():
            self.mon.stop()
            return "Stopping monitor…"
        return "Monitor not running."

    def status(self):
        if self.mon and self.mon.is_alive():
            s = self.mon.state
            state = "unknown" if s is None else ("Tor OK" if s else "Tor DOWN")
            return f"Monitor: RUNNING  |  State: {state}"
        else:
            return "Monitor: STOPPED"

    def tail_logs(self, lines=30):
        try:
            with open(LOGFILE, "r") as f:
                data = f.readlines()[-lines:]
        except Exception:
            data = ["<no logs yet>"]
        return "".join(data)

    def test_warning(self):
        show_fullscreen_warning(self.cfg)
        return "Test warning closed."

    def show_cfg_path(self):
        return f"Using config: {self.cfg_path}\n(Edit with sudo if system path.)"

    def run(self, stdscr):
        curses.curs_set(0)
        h, w = stdscr.getmaxyx()
        msg = ""
        while True:
            stdscr.clear()
            title = f"{APP} — Tor Monitor"
            stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)

            for i, item in enumerate(self.ITEMS):
                attr = curses.A_REVERSE if i == self.idx else curses.A_NORMAL
                stdscr.addstr(2 + i, 4, item.ljust(20), attr)

            # footer / messages
            if msg:
                for i, line in enumerate(textwrap.wrap(msg, width=w - 8)):
                    stdscr.addstr(h - 3 - (len(textwrap.wrap(msg, width=w - 8)) - 1 - i), 4, line)

            stdscr.refresh()
            ch = stdscr.getch()
            if ch in (curses.KEY_UP, ord('k')):
                self.idx = (self.idx - 1) % len(self.ITEMS)
            elif ch in (curses.KEY_DOWN, ord('j')):
                self.idx = (self.idx + 1) % len(self.ITEMS)
            elif ch in (curses.KEY_ENTER, 10, 13):
                sel = self.ITEMS[self.idx]
                if sel == "Start Monitor":
                    msg = self.start_monitor()
                elif sel == "Stop Monitor":
                    msg = self.stop_monitor()
                elif sel == "Status":
                    msg = self.status()
                elif sel == "Tail Logs":
                    curses.endwin()
                    print("\n--- LOG TAIL ---")
                    print(self.tail_logs())
                    input("\nPress Enter to return to menu...")
                    stdscr = curses.initscr()
                    curses.curs_set(0)
                    h, w = stdscr.getmaxyx()
                    msg = "Logs displayed."
                elif sel == "Test Warning":
                    curses.endwin()
                    msg = self.test_warning()
                    stdscr = curses.initscr()
                    curses.curs_set(0)
                    h, w = stdscr.getmaxyx()
                elif sel == "Show Config Path":
                    msg = self.show_cfg_path()
                elif sel == "Quit":
                    if self.mon and self.mon.is_alive():
                        self.mon.stop()
                        time.sleep(0.2)
                    break
            elif ch in (ord('q'), 27):  # q or ESC
                if self.mon and self.mon.is_alive():
                    self.mon.stop()
                    time.sleep(0.2)
                break

# -------------- Entry point --------------
def main():
    cfg_file = ensure_user_cfg()
    cfg = parse_cfg(cfg_file)

    if os.geteuid() != 0:
        print("Note: run with sudo to allow network disable operations.\n")

    # If curses not desired/available, run headless monitor directly
    if not cfg["USE_CURSES"]:
        print(f"{APP} running without menu. Ctrl-C to stop.")
        mon = Monitor(cfg)
        mon.start()
        try:
            while mon.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            mon.stop()
        return

    try:
        curses.wrapper(MenuApp(cfg_file, cfg).run)
    except Exception as e:
        print("Curses failed; falling back to headless mode:", e)
        mon = Monitor(cfg)
        mon.start()
        try:
            while mon.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            mon.stop()

if __name__ == "__main__":
    main()
