#!/bin/bash
set -e
SERVICE_NAME="firenode-rpi"
sudo systemctl stop "${SERVICE_NAME}.service" 2>/dev/null || true
sudo systemctl disable "${SERVICE_NAME}.service" 2>/dev/null || true
sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
sudo systemctl daemon-reload
echo "Service removed: ${SERVICE_NAME}"
