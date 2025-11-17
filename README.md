# 🛡️ TorGuard

**Interactive Tor Monitor**
A Python utility for monitoring Tor connectivity with curses-based UI, emergency GUI alerts, and optional safe network disablement.

![TorGuard Screenshot Placeholder](https://img.shields.io/badge/status-active-brightgreen)
*Built with Python 3 | Supports Linux systems with optional GUI*

---

## 📌 Features

* **Live Monitoring**: Detects Tor activity via SOCKS ports and system processes.
* **Failsafe Network Kill**: Disables network (via `nmcli` or `ip link`) on Tor failure with optional confirmation.
* **Multiple UI Layers**:

  * Fullscreen **Tkinter** red-screen warning.
  * Terminal-safe **curses menu** interface.
  * **ASCII fallback** for headless environments.
* **Configurable**: Uses a user/system `.conf` file for ports, retry delays, interface safelists, and GUI behavior.
* **Fails Gracefully**: Grace-period + retries before triggering alert or action.

---

## ⚙️ Configuration

TorGuard uses the following config precedence:

1. `/etc/tor_guard.conf` (system)
2. `~/.config/tor_guard/tor_guard.conf` (user)

Default config on first run if none found:

```ini
SOCKS_PORTS=9050,9150
CHECK_HOSTS=127.0.0.1,::1
GRACE_SECONDS=8
RETRIES=2
CHECK_INTERVAL=3
REQUIRE_CONFIRM=true
USE_TK=true
USE_CURSES=true
RED_IMAGE_PATH=
INTERFACE_WHITELIST=
```

---

## 🚀 Usage

### 🔧 Launch

> **Note**: Requires root (`sudo`) to disable networking.

```bash
sudo python3 tor_guard.py
```

### 🧭 Menu Options

* **Start Monitor**: Begins background checking.
* **Stop Monitor**: Halts the active monitor thread.
* **Status**: Shows current Tor state (OK/DOWN).
* **Tail Logs**: Displays recent log entries.
* **Test Warning**: Triggers alert overlay.
* **Show Config Path**: Displays the path of the active config file.

---

## 🧠 How It Works

1. **Monitors SOCKS & Tor process** every few seconds.
2. On failure, waits grace period + retries.
3. Triggers fullscreen **red warning UI**.
4. Asks user to disable network (confirmation required unless overridden).
5. Supports **NetworkManager (`nmcli`)** or **raw interface down** via `ip`.

---

## 📓 Logs

Logs are written to:

```
/var/tmp/tor_guard.log
```

---

## 🔐 Safety Notes

* No automatic disablement without interactive confirmation (unless configured otherwise).
* Supports whitelist of interfaces to restrict which can be taken offline.
* Supports offline or GUI-less environments gracefully.

---

## 🛠 Dependencies

* Python 3.x
* `tkinter` (for GUI warning)
* `nmcli` or `ip` (for network control)
* `pgrep`, `socket`, `subprocess`, `curses` (standard in most Unix distros)

---

## 🧪 Testing / Development

You can trigger test warnings without killing Tor:

```bash
sudo python3 tor_guard.py
# then select 'Test Warning' from the menu
```

Or run headless mode if no terminal GUI is available:

```bash
USE_CURSES=false python3 tor_guard.py
```

---

## 📦 Packaging Suggestion

To distribute:

* Include `tor_guard.py`
* Package example config in `etc/tor_guard.conf`
* Optional: Systemd unit file for background monitoring

---

## 📄 License

MIT License – free to use, modify, distribute.

---

Let me know if you want a version with screenshots, badges, or a `systemd` service unit.
