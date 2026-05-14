#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/raspi/firenode-system"

cd "$APP_DIR"

PYTHON_BIN="python3"
if [ ! -d "venv" ]; then
  echo "No local venv found in $APP_DIR."
  echo "On Raspberry Pi, run: ./setup.sh"
  echo "On macOS/dev machines, create a compatible Python environment before running the app."
else
  PYTHON_BIN="$APP_DIR/venv/bin/python"
fi

"$PYTHON_BIN" - <<'PY'
import json
from pathlib import Path

path = Path("config.json")
cfg = {}
if path.exists():
    cfg = json.loads(path.read_text())

cfg.update({
    "role": "server",
    "operation_mode": "simulation",
    "remote_node_count": 3,
    "host": "0.0.0.0",
    "port": 8090,
    "camera_enabled": True,
    "thermal_enabled": True,
    "thermal_simulation": True,
    "lora_enabled": True,
    "lora_sim_interval_sec": 5,
    "lora_frequency_mhz": 433.0,
    "lora_spreading_factor": 7,
    "lora_bandwidth_khz": 125.0,
    "auto_start": False
})

path.write_text(json.dumps(cfg, indent=2) + "\n")
print("Simulation config written to", path)
PY

echo "Starting FireNode main dashboard simulation on http://127.0.0.1:8090"
exec "$PYTHON_BIN" app.py --host 0.0.0.0 --port 8090
