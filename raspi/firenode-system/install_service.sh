#!/bin/bash
set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="firenode-rpi"
USER_NAME="$(whoami)"

sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=FireNode RPi Unified Node/Main Server Web GUI
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${APP_DIR}
ExecStart=/bin/bash ${APP_DIR}/run.sh
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}.service"
sudo systemctl restart "${SERVICE_NAME}.service"

echo "Service installed and started: ${SERVICE_NAME}"
echo "Check status with: sudo systemctl status ${SERVICE_NAME}"
