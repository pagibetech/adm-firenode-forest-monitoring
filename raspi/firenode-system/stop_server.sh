#!/bin/bash
set +e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${1:-8090}"

echo "Stopping FireNode server on port $PORT..."

sudo systemctl stop firenode-rpi.service 2>/dev/null
sudo systemctl disable firenode-rpi.service 2>/dev/null

if command -v fuser >/dev/null 2>&1; then
  sudo fuser -k "${PORT}/tcp" 2>/dev/null
fi

pkill -f "$APP_DIR/app.py" 2>/dev/null

sleep 1
if command -v ss >/dev/null 2>&1; then
  if ss -ltnp 2>/dev/null | grep -q ":${PORT} "; then
    echo "WARNING: Port $PORT is still in use. Check it with: sudo ss -ltnp | grep ':$PORT'"
  else
    echo "Port $PORT is now free. You can run: ./run.sh"
  fi
else
  echo "Done. You can run: ./run.sh"
fi
