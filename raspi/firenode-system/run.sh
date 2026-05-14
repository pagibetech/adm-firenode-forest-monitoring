#!/bin/bash
set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

PORT="${PORT:-8090}"
HOST="${HOST:-0.0.0.0}"

if [ -x "$APP_DIR/venv/bin/python" ]; then
  PY="$APP_DIR/venv/bin/python"
else
  PY="python3"
fi

echo "Starting FireNode RPi server on port $PORT..."
echo "Project folder: $APP_DIR"
echo ""

exec "$PY" "$APP_DIR/app.py" --host "$HOST" --port "$PORT"
