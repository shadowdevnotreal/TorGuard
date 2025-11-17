#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TorGuard Configuration Editor - GUI tool for editing TorGuard configuration

Features:
- Visual editor for all config options
- Validation of inputs
- Platform-aware defaults
- Save/Load configuration
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Dict, Any
import platform


class TorGuardConfigEditor:
    """GUI editor for TorGuard configuration."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TorGuard Configuration Editor")
        self.root.geometry("700x800")

        # Detect platform
        self.system = platform.system().lower()

        # Configuration file paths
        self.sys_cfg = Path("/etc/tor_guard.conf")
        self.usr_cfg = Path.home() / ".config" / "tor_guard" / "tor_guard.conf"

        # Current config file
        self.current_file = self.usr_cfg if self.usr_cfg.exists() else self.sys_cfg

        # Config variables
        self.vars: Dict[str, Any] = {}

        # Create UI
        self.create_ui()

        # Load existing config
        self.load_config()

    def create_ui(self) -> None:
        """Create the user interface."""
        # Title
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            title_frame,
            text="TorGuard Configuration Editor",
            font=("Arial", 16, "bold")
        )
        title_label.pack()

        # File info
        file_frame = ttk.Frame(self.root, padding="10")
        file_frame.pack(fill=tk.X)

        self.file_label = ttk.Label(file_frame, text=f"Editing: {self.current_file}")
        self.file_label.pack(side=tk.LEFT)

        ttk.Button(file_frame, text="Choose File", command=self.choose_file).pack(side=tk.RIGHT)

        # Scrollable frame for config options
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Configuration options
        options_frame = ttk.LabelFrame(scrollable_frame, text="Configuration Options", padding="10")
        options_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # SOCKS_PORTS
        self.create_entry(
            options_frame,
            "SOCKS_PORTS",
            "SOCKS Ports (comma-separated):",
            "9050,9150",
            "Ports to probe for Tor SOCKS proxy (e.g., 9050,9150)"
        )

        # CHECK_HOSTS
        self.create_entry(
            options_frame,
            "CHECK_HOSTS",
            "Check Hosts (comma-separated):",
            "127.0.0.1,::1",
            "Localhost addresses to check (IPv4 and IPv6)"
        )

        # GRACE_SECONDS
        self.create_entry(
            options_frame,
            "GRACE_SECONDS",
            "Grace Period (seconds):",
            "8",
            "Seconds to wait before treating failure as 'real'"
        )

        # RETRIES
        self.create_entry(
            options_frame,
            "RETRIES",
            "Retry Attempts:",
            "2",
            "Consecutive failed checks before triggering action"
        )

        # CHECK_INTERVAL
        self.create_entry(
            options_frame,
            "CHECK_INTERVAL",
            "Check Interval (seconds):",
            "3",
            "How often to probe Tor connectivity"
        )

        # REQUIRE_CONFIRM
        self.create_checkbox(
            options_frame,
            "REQUIRE_CONFIRM",
            "Require Confirmation Before Network Disable",
            True,
            "Ask for 'YES' confirmation before disabling network (recommended)"
        )

        # USE_TK
        self.create_checkbox(
            options_frame,
            "USE_TK",
            "Use Tkinter GUI Warning",
            True,
            "Show full-screen red warning using Tkinter"
        )

        # USE_CURSES
        self.create_checkbox(
            options_frame,
            "USE_CURSES",
            "Use Curses Menu Interface",
            True,
            "Enable interactive terminal menu"
        )

        # RED_IMAGE_PATH
        self.create_file_entry(
            options_frame,
            "RED_IMAGE_PATH",
            "Warning Image Path (optional):",
            "",
            "Path to custom warning image to display"
        )

        # INTERFACE_WHITELIST
        self.create_entry(
            options_frame,
            "INTERFACE_WHITELIST",
            "Interface Whitelist (comma-separated, optional):",
            "",
            "Specific interfaces to consider for network disable (leave empty for auto)"
        )

        # Platform info
        platform_frame = ttk.LabelFrame(scrollable_frame, text="Platform Information", padding="10")
        platform_frame.pack(fill=tk.X, padx=10, pady=5)

        platform_text = f"Operating System: {self.system.capitalize()}\n"
        if self.system == "linux":
            platform_text += "Network control: NetworkManager (nmcli) or ip command"
        elif self.system == "darwin":
            platform_text += "Network control: networksetup command"
        elif self.system == "windows":
            platform_text += "Network control: netsh command"

        ttk.Label(platform_frame, text=platform_text, justify=tk.LEFT).pack()

        # Buttons
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(button_frame, text="Save", command=self.save_config, style="Accent.TButton").pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Load", command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_defaults).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Close", command=self.root.quit).pack(side=tk.RIGHT, padx=5)

    def create_entry(
        self, parent: ttk.Frame, key: str, label: str, default: str, tooltip: str
    ) -> None:
        """Create a labeled entry widget."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text=label, width=35, anchor=tk.W).pack(side=tk.LEFT)

        var = tk.StringVar(value=default)
        self.vars[key] = var

        entry = ttk.Entry(frame, textvariable=var, width=40)
        entry.pack(side=tk.LEFT, padx=5)

        # Tooltip
        self.create_tooltip(entry, tooltip)

    def create_checkbox(
        self, parent: ttk.Frame, key: str, label: str, default: bool, tooltip: str
    ) -> None:
        """Create a checkbox widget."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)

        var = tk.BooleanVar(value=default)
        self.vars[key] = var

        cb = ttk.Checkbutton(frame, text=label, variable=var)
        cb.pack(anchor=tk.W)

        # Tooltip
        self.create_tooltip(cb, tooltip)

    def create_file_entry(
        self, parent: ttk.Frame, key: str, label: str, default: str, tooltip: str
    ) -> None:
        """Create an entry with file browser button."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text=label, width=35, anchor=tk.W).pack(side=tk.LEFT)

        var = tk.StringVar(value=default)
        self.vars[key] = var

        entry = ttk.Entry(frame, textvariable=var, width=30)
        entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            frame,
            text="Browse...",
            command=lambda: self.browse_file(var),
            width=10
        ).pack(side=tk.LEFT)

        # Tooltip
        self.create_tooltip(entry, tooltip)

    def create_tooltip(self, widget, text: str) -> None:
        """Create a tooltip for a widget."""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")

            label = tk.Label(
                tooltip,
                text=text,
                background="yellow",
                relief=tk.SOLID,
                borderwidth=1,
                wraplength=300,
                justify=tk.LEFT
            )
            label.pack()

            widget.tooltip = tooltip

        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def browse_file(self, var: tk.StringVar) -> None:
        """Open file browser dialog."""
        filename = filedialog.askopenfilename(
            title="Select Warning Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif"), ("All files", "*.*")]
        )
        if filename:
            var.set(filename)

    def choose_file(self) -> None:
        """Choose which config file to edit."""
        filename = filedialog.askopenfilename(
            title="Select Config File",
            initialdir=str(self.usr_cfg.parent),
            filetypes=[("Config files", "*.conf"), ("All files", "*.*")]
        )
        if filename:
            self.current_file = Path(filename)
            self.file_label.config(text=f"Editing: {self.current_file}")
            self.load_config()

    def load_config(self) -> None:
        """Load configuration from file."""
        if not self.current_file.exists():
            messagebox.showinfo("Info", f"Config file not found: {self.current_file}\nUsing defaults.")
            return

        try:
            with open(self.current_file, 'r') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = [x.strip() for x in line.split("=", 1)]

                if key in self.vars:
                    if isinstance(self.vars[key], tk.BooleanVar):
                        bool_val = value.lower() in ("1", "true", "yes", "y", "on")
                        self.vars[key].set(bool_val)
                    else:
                        self.vars[key].set(value)

            messagebox.showinfo("Success", "Configuration loaded successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")

    def save_config(self) -> None:
        """Save configuration to file."""
        # Validate inputs
        if not self.validate_config():
            return

        # Ensure directory exists
        self.current_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.current_file, 'w') as f:
                f.write("# TorGuard Configuration File\n")
                f.write("# Auto-generated by TorGuard Config Editor\n\n")

                for key, var in self.vars.items():
                    if isinstance(var, tk.BooleanVar):
                        value = "true" if var.get() else "false"
                    else:
                        value = var.get()

                    f.write(f"{key}={value}\n")

            messagebox.showinfo("Success", f"Configuration saved to:\n{self.current_file}")

        except PermissionError:
            messagebox.showerror(
                "Permission Denied",
                f"Cannot write to {self.current_file}\n\nTry running with sudo:\n  sudo torguard-config"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")

    def validate_config(self) -> bool:
        """Validate configuration values."""
        # Validate ports
        ports_str = self.vars["SOCKS_PORTS"].get()
        try:
            ports = [int(p.strip()) for p in ports_str.split(",") if p.strip()]
            for port in ports:
                if not 1 <= port <= 65535:
                    messagebox.showerror("Validation Error", f"Invalid port number: {port}\nMust be between 1 and 65535")
                    return False
        except ValueError:
            messagebox.showerror("Validation Error", "SOCKS_PORTS must be comma-separated numbers")
            return False

        # Validate numeric values
        try:
            grace = int(self.vars["GRACE_SECONDS"].get())
            if grace < 0:
                messagebox.showerror("Validation Error", "GRACE_SECONDS must be non-negative")
                return False
        except ValueError:
            messagebox.showerror("Validation Error", "GRACE_SECONDS must be a number")
            return False

        try:
            retries = int(self.vars["RETRIES"].get())
            if retries < 1:
                messagebox.showerror("Validation Error", "RETRIES must be at least 1")
                return False
        except ValueError:
            messagebox.showerror("Validation Error", "RETRIES must be a number")
            return False

        try:
            interval = int(self.vars["CHECK_INTERVAL"].get())
            if interval < 1:
                messagebox.showerror("Validation Error", "CHECK_INTERVAL must be at least 1")
                return False
        except ValueError:
            messagebox.showerror("Validation Error", "CHECK_INTERVAL must be a number")
            return False

        # Validate image path if provided
        img_path = self.vars["RED_IMAGE_PATH"].get().strip()
        if img_path:
            path = Path(img_path).expanduser()
            if not path.exists():
                result = messagebox.askyesno(
                    "Warning",
                    f"Image file does not exist:\n{path}\n\nContinue anyway?"
                )
                if not result:
                    return False

        return True

    def reset_defaults(self) -> None:
        """Reset all values to defaults."""
        result = messagebox.askyesno(
            "Confirm Reset",
            "Reset all values to defaults?\nUnsaved changes will be lost."
        )
        if result:
            self.vars["SOCKS_PORTS"].set("9050,9150")
            self.vars["CHECK_HOSTS"].set("127.0.0.1,::1")
            self.vars["GRACE_SECONDS"].set("8")
            self.vars["RETRIES"].set("2")
            self.vars["CHECK_INTERVAL"].set("3")
            self.vars["REQUIRE_CONFIRM"].set(True)
            self.vars["USE_TK"].set(True)
            self.vars["USE_CURSES"].set(True)
            self.vars["RED_IMAGE_PATH"].set("")
            self.vars["INTERFACE_WHITELIST"].set("")


def main():
    """Main entry point."""
    root = tk.Tk()
    app = TorGuardConfigEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
