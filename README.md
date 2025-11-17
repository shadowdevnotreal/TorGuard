# 🛡️ TorGuard

**Your Last Line of Defense Against Tor Connection Failures**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-green.svg)](https://www.python.org/)
![Status](https://img.shields.io/badge/status-active-brightgreen)
[![CI](https://img.shields.io/badge/CI-passing-success)](https://github.com/shadowdevnotreal/TorGuard/actions)

> *A lightweight, zero-dependency privacy guardian that automatically detects Tor failures and protects you from accidental unencrypted traffic.*

*Built with Python 3 | Cross-platform support for Linux, macOS, and Windows*

---

## 🎯 What is TorGuard?

TorGuard is a **privacy-focused monitoring tool** that continuously watches your Tor connection and immediately alerts you when it fails—before you accidentally expose your real IP address or leak sensitive data.

When Tor goes down, TorGuard:
- 🚨 **Displays a full-screen warning** (GUI or terminal)
- 🔒 **Optionally disables your network** (with your explicit consent)
- 📝 **Logs all events** for audit trail
- ⚡ **Reacts in seconds** with configurable grace periods

---

## ✨ Features

### 🔍 **Dual Tor Detection**
- **Live Monitoring**: Detects Tor activity via SOCKS ports (9050, 9150) and system processes
- Process monitoring with exact match (`tor` daemon detection)
- Configurable check intervals and grace periods

### 🎨 **Multi-Modal Warning System**
- **Tkinter Full-Screen GUI**: Unmissable red warning dialog
- **Custom Image Overlay**: Display your own warning image via `display` or `feh`
- **ASCII Terminal Fallback**: Works in headless environments

### 🌐 **Smart Network Control (Cross-Platform)**
- **Linux**: NetworkManager (`nmcli`) or direct interface control (`ip link`)
- **macOS**: networksetup command for network service management
- **Windows**: netsh command for interface control
- Interface whitelisting support
- Explicit user confirmation before network disable (recommended)
- Platform-aware re-enable instructions

### ⚙️ **Production-Ready**
- **Zero external dependencies** (pure Python standard library)
- Thread-safe monitoring with proper locking
- Comprehensive logging (stdlib `logging` module)
- **Fails Gracefully**: Grace-period + retries to prevent false positives
- Command-line arguments for automation

### 🎛️ **Interactive Menu**
- **Curses-based terminal UI** (headless-safe)
- Start/stop monitoring on demand
- Live status display (Tor OK/DOWN)
- Log tail viewer
- Test warning system

### 🎨 **NEW: GUI Configuration Editor**
- Visual editor for all configuration options
- Input validation and helpful tooltips
- Platform-aware defaults
- No command-line knowledge required
- Save/load configurations easily

### 🔗 **NEW: Tor Integration**
- Automatic Tor Browser detection
- Process monitoring for Tor Browser
- Control port discovery
- torsocks integration check
- Comprehensive Tor installation info

### 🧪 **NEW: Testing & CI/CD**
- Comprehensive unit test suite with pytest
- Cross-platform CI testing (Linux, macOS, Windows)
- Code quality checks (flake8, black, mypy)
- Security scanning with bandit
- Automated releases with GitHub Actions

---

## 📦 Installation

### Automated Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/shadowdevnotreal/TorGuard.git
cd TorGuard

# Run automated installer (Linux/macOS)
sudo ./install.sh
```

The installer will:
- ✅ Detect your operating system
- ✅ Install required dependencies
- ✅ Copy files to system directories
- ✅ Set up systemd service (Linux only)
- ✅ Install GUI config editor

### Manual Installation

#### Prerequisites by Platform

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install python3 python3-tk iproute2 procps network-manager
```

**Linux (Fedora/RHEL):**
```bash
sudo dnf install python3 python3-tkinter iproute procps-ng NetworkManager
```

**Linux (Arch):**
```bash
sudo pacman -S python3 tk iproute2 procps-ng networkmanager
```

**macOS:**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3
brew install python3
```

**Windows:**
- Download and install [Python 3.8+](https://www.python.org/downloads/windows/)
- Ensure Python is added to PATH during installation

**Optional GUI Dependencies:**
- `python3-tk` (Tkinter for GUI warnings and config editor)
- `imagemagick` or `feh` (Linux/macOS: for custom image overlays)

### Manual Setup

```bash
# Clone the repository
git clone https://github.com/shadowdevnotreal/TorGuard.git
cd TorGuard

# Make executable (Linux/macOS)
chmod +x tor_guard.py torguard_config_editor.py tor_integration.py

# Copy to system path (Linux/macOS)
sudo cp tor_guard.py /usr/local/bin/torguard
sudo cp torguard_config_editor.py /usr/local/bin/torguard-config
sudo cp tor_integration.py /usr/local/bin/torguard-info

# Windows: Add TorGuard directory to PATH or create shortcuts
```

---

## 🚀 Quick Start

### Basic Usage

> **Note**: Requires root (`sudo` on Linux/macOS, Administrator on Windows) to disable networking.

```bash
# Run with interactive menu (recommended)
sudo torguard                    # or: sudo python3 tor_guard.py

# Run in headless mode (for servers/automation)
sudo torguard --no-menu

# Enable debug logging
sudo torguard --debug

# Show config file location
torguard --config-path

# Edit configuration with GUI
torguard-config                  # or: python3 torguard_config_editor.py

# Check Tor installation info
torguard-info                    # or: python3 tor_integration.py
```

### First Run

1. **Start TorGuard** with `sudo python3 tor_guard.py`
2. Use **arrow keys** or **j/k** to navigate the curses menu
3. Select **"Start Monitor"** and press Enter
4. Monitor will continuously check Tor connectivity
5. Press **'q'** or select **"Quit"** to exit

### Menu Options

* **Start Monitor**: Begins background checking
* **Stop Monitor**: Halts the active monitor thread
* **Status**: Shows current Tor state (OK/DOWN/unknown)
* **Tail Logs**: Displays recent log entries
* **Test Warning**: Triggers alert overlay without killing network
* **Show Config Path**: Displays the path of the active config file

---

## ⚙️ Configuration

TorGuard uses the following config precedence:
1. `/etc/tor_guard.conf` (system-wide, requires sudo)
2. `~/.config/tor_guard/tor_guard.conf` (user-specific, auto-created)

Default config created on first run if none found:

### Configuration Options

```ini
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
```

### Example: Custom Warning Image

```bash
# Edit your config
nano ~/.config/tor_guard/tor_guard.conf

# Add this line:
RED_IMAGE_PATH=~/Pictures/tor_warning.png

# Ensure you have an image viewer installed
sudo apt-get install feh   # or imagemagick
```

---

## 📖 Usage Examples

### Example 1: Desktop User

```bash
# Run with GUI warnings
sudo python3 tor_guard.py

# Start monitor from menu
# If Tor fails, you'll see a full-screen red warning
# Close your browser, then choose to disable network
```

### Example 2: Server/Headless

```bash
# Run without menu, log to file
sudo python3 tor_guard.py --no-menu --debug >> /var/log/torguard.log 2>&1 &

# Check logs
tail -f /var/tmp/tor_guard.log
```

### Example 3: Custom Config

```bash
# Create custom config
cat > /tmp/my_tor_config.conf <<EOF
SOCKS_PORTS=9050
CHECK_INTERVAL=5
RETRIES=3
GRACE_SECONDS=10
EOF

# Use it
sudo python3 tor_guard.py --config /tmp/my_tor_config.conf
```

### Example 4: Automation with Systemd

```bash
# Add to systemd (create /etc/systemd/system/torguard.service)
[Unit]
Description=TorGuard - Tor Connection Monitor
After=network.target tor.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/TorGuard/tor_guard.py --no-menu
Restart=always
User=root

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable torguard
sudo systemctl start torguard
```

---

## 🧪 Testing

### Test the Warning System

```bash
# Start TorGuard
sudo python3 tor_guard.py

# From menu, select "Test Warning"
# This will show the warning screen without disabling network
```

### Simulate Tor Failure

```bash
# In one terminal, start TorGuard
sudo python3 tor_guard.py

# In another terminal, stop Tor
sudo systemctl stop tor

# Watch TorGuard react with warning and network disable option
```

---

## 🧠 How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                         TorGuard Architecture                    │
└─────────────────────────────────────────────────────────────────┘

                    ┌───────────────────┐
                    │   Main Thread     │
                    │  (Curses Menu)    │
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │ Monitor Thread    │
                    │  (Background)     │
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │  Tor Detection    │
                    │ (every N seconds) │
                    └────────┬──────────┘
                             │
                   ┌─────────▼────────────┐
                   │   Tor Alive?         │
                   │ (SOCKS + Process)    │
                   └─┬────────────────┬───┘
                     │ YES            │ NO
                     │                │
                ┌────▼─────┐    ┌────▼──────┐
                │ Continue │    │ Grace +   │
                │ Monitor  │    │ Retries   │
                └──────────┘    └────┬──────┘
                                     │
                              ┌──────▼──────────┐
                              │ Still Down?     │
                              └─┬───────────┬───┘
                                │ YES       │ NO
                                │           │
                         ┌──────▼──┐   ┌────▼─────┐
                         │ WARNING │   │ Continue │
                         │ DISPLAY │   │ Monitor  │
                         └──────┬──┘   └──────────┘
                                │
                         ┌──────▼──────────┐
                         │ User Confirms?  │
                         └─┬──────────┬────┘
                           │ YES      │ NO
                           │          │
                    ┌──────▼─────┐  ┌─▼────────┐
                    │ Disable    │  │ Continue │
                    │ Network    │  │ Monitor  │
                    └──────┬─────┘  └──────────┘
                           │
                    ┌──────▼──────┐
                    │ Exit with   │
                    │ Instructions│
                    └─────────────┘
```

### Detection Algorithm

1. **Monitors SOCKS & Tor process** every few seconds (configurable)
2. **Primary Check**: Attempt TCP connection to `127.0.0.1:9050` (SOCKS proxy)
3. **Fallback Check**: Look for running `tor` process (exact match with `pgrep -x`)
4. On failure, waits **grace period + retries** to avoid false positives
5. **Grace Period**: Wait N seconds to avoid temporary glitches
6. **Retry Logic**: Perform M consecutive checks before declaring failure
7. Triggers fullscreen **red warning UI** (Tkinter/Image/ASCII)
8. Asks user to disable network (confirmation required unless overridden)
9. **Action**: Disable via **NetworkManager (`nmcli`)** or **raw interface down** via `ip`

---

## 🛠️ Troubleshooting

### "pgrep command not found"

```bash
# Install procps
sudo apt-get install procps      # Debian/Ubuntu
sudo dnf install procps-ng        # Fedora
```

### "ip command not found"

```bash
# Install iproute2
sudo apt-get install iproute2     # Debian/Ubuntu
sudo dnf install iproute          # Fedora
```

### "Tkinter not available"

```bash
# Install Python Tkinter
sudo apt-get install python3-tk   # Debian/Ubuntu
sudo dnf install python3-tkinter  # Fedora
```

### Warning doesn't appear

- Check that `USE_TK=true` in config
- Verify `DISPLAY` environment variable is set: `echo $DISPLAY`
- Try ASCII fallback by setting `USE_TK=false`
- Test with: Select "Test Warning" from the menu

### Network disable requires sudo

```bash
# Always run with sudo for network control
sudo python3 tor_guard.py
```

### False positives (Tor is up but warnings appear)

```ini
# Increase grace period and retries in config
GRACE_SECONDS=15
RETRIES=3
CHECK_INTERVAL=5
```

### Running in headless mode

```bash
# Disable curses menu
sudo python3 tor_guard.py --no-menu

# Or set in config
USE_CURSES=false
```

---

## 🔒 Security Considerations

### Why Root Access?

TorGuard requires `sudo` **only** for disabling network interfaces. The monitoring functionality works without root, but network disable operations need elevated privileges.

### Safety Features

- **Explicit Confirmation**: By default, requires typing `YES` before disabling network
- **No automatic disablement** without interactive confirmation (unless configured otherwise)
- **Logging**: All actions logged to `/var/tmp/tor_guard.log` with timestamps
- **Thread-Safe**: Proper locking prevents race conditions
- **Graceful Shutdown**: Uses `sys.exit()` instead of `os._exit()` for proper cleanup
- **Timeout Protection**: All subprocess calls have timeouts to prevent hangs
- **Interface Whitelist**: Supports whitelist of interfaces to restrict which can be taken offline
- **Offline-safe**: Supports offline or GUI-less environments gracefully

### Privacy Protection

- **Zero External Dependencies**: No telemetry or phone-home functionality
- **Local Operation**: All checks performed on localhost
- **No Data Collection**: Does not log browsing activity or personal data

---

## 📊 Logs

Logs are written to:

```
/var/tmp/tor_guard.log
```

TorGuard logs with the following format:

```
2025-11-17 14:23:01,123 - TorGuard - INFO - Monitor started
2025-11-17 14:23:04,456 - TorGuard - WARNING - Tor appears down; grace+retries begin
2025-11-17 14:23:12,789 - TorGuard - INFO - Tor recovered on retry 2
2025-11-17 14:25:30,012 - TorGuard - ERROR - Persistent Tor outage detected -> triggering warning
2025-11-17 14:25:45,345 - TorGuard - CRITICAL - Network disabled by tool; exiting monitor
```

### View Logs

```bash
# From menu: Select "Tail Logs"

# Or directly:
tail -f /var/tmp/tor_guard.log

# Filter for errors:
grep ERROR /var/tmp/tor_guard.log
```

---

## 🎯 Command-Line Reference

```
usage: tor_guard.py [-h] [--no-menu] [--debug] [--config-path] [--config CONFIG]

TorGuard - Monitor Tor connectivity and protect against leaks

optional arguments:
  -h, --help       show this help message and exit
  --no-menu        Run without curses menu (headless mode)
  --debug          Enable debug logging
  --config-path    Show config file path and exit
  --config CONFIG  Use specific config file

Examples:
  sudo python3 tor_guard.py              # Run with menu interface
  sudo python3 tor_guard.py --no-menu    # Run in headless mode
  sudo python3 tor_guard.py --debug      # Enable debug logging
  python3 tor_guard.py --config-path     # Show config file location

Note: Requires sudo for network disable operations.
```

---

## 🛠 Dependencies

**Required:**
- Python 3.6+
- `iproute2` (for `ip` command)
- `procps` or `procps-ng` (for `pgrep`)
- Standard library modules: `socket`, `subprocess`, `curses`, `threading`, `argparse`, `logging`

**Optional:**
- `python3-tk` (Tkinter for GUI warning)
- `network-manager` (`nmcli` for NetworkManager integration)
- `imagemagick` or `feh` (for custom image overlays)

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Recently Implemented ✅

- [x] ~~Add systemd integration examples~~ - **Implemented!** Service file and installer included
- [x] ~~macOS support (using `networksetup`)~~ - **Implemented!** Full macOS network control
- [x] ~~Windows support (using `netsh`)~~ - **Implemented!** Full Windows network control
- [x] ~~GUI configuration editor~~ - **Implemented!** Tkinter-based visual editor
- [x] ~~Integration with other Tor management tools~~ - **Implemented!** Tor Browser detection and integration
- [x] ~~Unit tests and CI/CD~~ - **Implemented!** Pytest suite and GitHub Actions

### Areas for Future Improvement

- [ ] Email/SMS notifications for Tor failures
- [ ] Desktop notifications (libnotify, Windows Toast, macOS Notification Center)
- [ ] Web dashboard for remote monitoring
- [ ] Screenshots and demo GIFs for README
- [ ] Snap/Flatpak/Homebrew packaging
- [ ] Browser extension integration

### Development Setup

```bash
# Clone the repo
git clone https://github.com/shadowdevnotreal/TorGuard.git
cd TorGuard

# Install development dependencies
pip install -r requirements-dev.txt

# Run unit tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=. --cov-report=html

# Check code quality
flake8 .
black --check .
mypy tor_guard.py

# Run application in debug mode
sudo python3 tor_guard.py --debug

# Test GUI config editor
python3 torguard_config_editor.py

# Check Tor integration
python3 tor_integration.py
```

### Code Style

- Follow PEP 8
- Add type hints to all functions
- Use descriptive variable names
- Add docstrings to all public functions
- Log errors with appropriate severity

---

## 📦 Packaging Suggestion

To distribute:

- Include `tor_guard.py`
- Package example config in `etc/tor_guard.conf`
- Optional: Systemd unit file for background monitoring
- Optional: Desktop launcher file

---

## 📜 License

This project is licensed under the **MIT License** - free to use, modify, distribute.

```
MIT License

Copyright (c) 2025 TorGuard Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Acknowledgments

- The Tor Project for creating the anonymity network
- Python community for the excellent standard library
- Privacy advocates who inspired this tool

---

## 📞 Support

### Get Help

- **Issues**: [GitHub Issues](https://github.com/shadowdevnotreal/TorGuard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/shadowdevnotreal/TorGuard/discussions)

### Stay Updated

⭐ Star this repo to stay notified of updates!

---

## 🔗 Related Projects

- [Tor Browser](https://www.torproject.org/download/) - Official Tor browser
- [torsocks](https://github.com/dgoulet/torsocks) - Use SOCKS-friendly apps with Tor
- [OnionShare](https://github.com/micahflee/onionshare) - Share files anonymously

---

<div align="center">

**Built with 🛡️ for privacy-conscious users**

If TorGuard helped protect your privacy, consider sharing it with others!

[⬆ Back to Top](#-torguard)

</div>
