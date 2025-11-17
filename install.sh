#!/bin/bash
# TorGuard Installation Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}TorGuard Installation Script${NC}"
echo "=============================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    echo -e "${RED}Unsupported OS: $OSTYPE${NC}"
    exit 1
fi

echo -e "Detected OS: ${GREEN}$OS${NC}"

# Install dependencies based on OS
install_dependencies() {
    echo -e "\n${YELLOW}Installing dependencies...${NC}"

    if [[ "$OS" == "linux" ]]; then
        if command -v apt-get &> /dev/null; then
            apt-get update
            apt-get install -y python3 python3-tk iproute2 procps network-manager
        elif command -v dnf &> /dev/null; then
            dnf install -y python3 python3-tkinter iproute procps-ng NetworkManager
        elif command -v pacman &> /dev/null; then
            pacman -Sy --noconfirm python3 tk iproute2 procps-ng networkmanager
        else
            echo -e "${YELLOW}Warning: Could not detect package manager. Please install dependencies manually.${NC}"
        fi
    elif [[ "$OS" == "macos" ]]; then
        if ! command -v brew &> /dev/null; then
            echo -e "${RED}Homebrew not found. Please install Homebrew first: https://brew.sh${NC}"
            exit 1
        fi
        brew install python3
    fi

    echo -e "${GREEN}Dependencies installed successfully${NC}"
}

# Install TorGuard
install_torguard() {
    echo -e "\n${YELLOW}Installing TorGuard...${NC}"

    # Copy main script
    cp tor_guard.py /usr/local/bin/tor_guard.py
    chmod +x /usr/local/bin/tor_guard.py

    # Create symlink
    ln -sf /usr/local/bin/tor_guard.py /usr/local/bin/torguard

    echo -e "${GREEN}TorGuard installed to /usr/local/bin/tor_guard.py${NC}"
}

# Install systemd service (Linux only)
install_systemd_service() {
    if [[ "$OS" == "linux" ]]; then
        echo -e "\n${YELLOW}Installing systemd service...${NC}"

        # Copy service file
        cp torguard.service /etc/systemd/system/torguard.service

        # Reload systemd
        systemctl daemon-reload

        echo -e "${GREEN}Systemd service installed${NC}"
        echo -e "To enable at boot: ${YELLOW}sudo systemctl enable torguard${NC}"
        echo -e "To start now: ${YELLOW}sudo systemctl start torguard${NC}"
        echo -e "To check status: ${YELLOW}sudo systemctl status torguard${NC}"
    fi
}

# Install config editor
install_config_editor() {
    echo -e "\n${YELLOW}Installing configuration editor...${NC}"

    if [[ -f "torguard_config_editor.py" ]]; then
        cp torguard_config_editor.py /usr/local/bin/torguard-config
        chmod +x /usr/local/bin/torguard-config
        echo -e "${GREEN}Config editor installed: torguard-config${NC}"
    fi
}

# Main installation
main() {
    install_dependencies
    install_torguard
    install_systemd_service
    install_config_editor

    echo -e "\n${GREEN}===============================================${NC}"
    echo -e "${GREEN}TorGuard installation completed successfully!${NC}"
    echo -e "${GREEN}===============================================${NC}"
    echo -e "\nQuick start:"
    echo -e "  ${YELLOW}sudo torguard${NC}           - Run with interactive menu"
    echo -e "  ${YELLOW}sudo torguard --no-menu${NC} - Run in headless mode"
    echo -e "  ${YELLOW}torguard-config${NC}         - Edit configuration (GUI)"
    echo -e "\nFor more help, see: https://github.com/shadowdevnotreal/TorGuard"
}

# Run installation
main
