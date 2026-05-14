#!/bin/bash
set +e

SERVICE_NAME="firenode-lora-gateway"

echo "Stopping ${SERVICE_NAME}.service..."
sudo systemctl stop "${SERVICE_NAME}.service" 2>/dev/null
sudo systemctl disable "${SERVICE_NAME}.service" 2>/dev/null
echo "Done."
