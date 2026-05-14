#!/bin/bash
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="firenode-lora-gateway"
USER_NAME="$(whoami)"
SERIAL_PORT="${1:-/dev/ttyUSB0}"
BAUD="${2:-115200}"
API_BASE="${3:-http://127.0.0.1:8090}"

if [ -x "$APP_DIR/venv/bin/python" ]; then
  PY="$APP_DIR/venv/bin/python"
else
  PY="python3"
fi

sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=FireNode LoRa Serial Gateway Bridge
After=network-online.target firenode-rpi.service
Wants=network-online.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${APP_DIR}
ExecStart=${PY} ${APP_DIR}/lora_gateway_serial.py --port ${SERIAL_PORT} --baud ${BAUD} --api-base ${API_BASE}
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
echo "Serial port: ${SERIAL_PORT}"
echo "API base: ${API_BASE}"
echo "Check status with: sudo systemctl status ${SERVICE_NAME}"
