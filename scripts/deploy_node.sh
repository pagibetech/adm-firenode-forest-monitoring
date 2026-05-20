#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SSH_KEY="${ADM_FIRE_SSH_KEY:-${HOME}/admfire}"
SSH_USER="${ADM_FIRE_SSH_USER:-betech}"
REMOTE_BASE="${ADM_FIRE_REMOTE_BASE:-/home/${SSH_USER}/admfire}"
APP_REL="raspi/firenode-system"
REMOTE_APP="${REMOTE_BASE}/${APP_REL}"
MAIN_SERVER_IP_DEFAULT="${ADM_FIRE_MAIN_SERVER_IP:-192.168.9.51}"
REMOTE_NODE_IPS_DEFAULT="${ADM_FIRE_REMOTE_NODE_IPS:-192.168.9.52,192.168.9.53,192.168.9.54}"
PORT="${ADM_FIRE_PORT:-8090}"

usage() {
  cat <<EOF
Usage:
  $0 <node-name> <node-ip> [role] [main-server-ip] [options]

Examples:
  $0 node_01 192.168.9.52 node_01 192.168.9.51
  $0 main_server 192.168.9.51 main_server 192.168.9.51 --install-service

Options:
  --install-service   Install, enable, and start the optional systemd service.
  --start             Start the app once with nohup after deployment.
  --validate          Run lightweight remote checks after deployment.
  --skip-setup        Copy/configure only; skip apt/venv dependency setup.
  -h, --help          Show this help.

Environment overrides:
  ADM_FIRE_SSH_KEY=/path/to/key
  ADM_FIRE_SSH_USER=betech
  ADM_FIRE_REMOTE_BASE=/home/betech/admfire
  ADM_FIRE_MAIN_SERVER_IP=192.168.9.51
  ADM_FIRE_REMOTE_NODE_IPS=192.168.9.52,192.168.9.53,192.168.9.54
  ADM_FIRE_PORT=8090
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

NODE_NAME="${1:-}"
NODE_IP="${2:-}"
ROLE="${3:-node}"
MAIN_SERVER_IP="${4:-$MAIN_SERVER_IP_DEFAULT}"
shift $(( $# >= 4 ? 4 : $# ))

INSTALL_SERVICE="0"
START_AFTER_DEPLOY="0"
VALIDATE_AFTER_DEPLOY="0"
SKIP_SETUP="0"

for arg in "$@"; do
  case "$arg" in
    --install-service) INSTALL_SERVICE="1" ;;
    --start) START_AFTER_DEPLOY="1" ;;
    --validate) VALIDATE_AFTER_DEPLOY="1" ;;
    --skip-setup) SKIP_SETUP="1" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; usage; exit 2 ;;
  esac
done

if [ -z "$NODE_NAME" ] || [ -z "$NODE_IP" ]; then
  usage
  exit 2
fi

ROLE_NORMALIZED="$(printf '%s' "$ROLE" | tr '[:upper:]-' '[:lower:]_')"
case "$ROLE_NORMALIZED" in
  main_server|server|node_main_center)
    APP_ROLE="server"
    ROLE="main_server"
    ;;
  node|node_01|node_02|node_03|node_1|node_2|node_3)
    APP_ROLE="node"
    case "$ROLE_NORMALIZED" in
      node_1) ROLE="node_01" ;;
      node_2) ROLE="node_02" ;;
      node_3) ROLE="node_03" ;;
      node) ROLE="$NODE_NAME" ;;
      *) ROLE="$ROLE_NORMALIZED" ;;
    esac
    ;;
  *)
    echo "Role must be one of: main_server, server, node, node_01, node_02, node_03." >&2
    exit 2
    ;;
esac

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key not found: $SSH_KEY" >&2
  exit 1
fi

SSH_OPTS=(
  -i "$SSH_KEY"
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=10
)

ssh_remote() {
  ssh "${SSH_OPTS[@]}" "${SSH_USER}@${NODE_IP}" "$@"
}

ssh_remote_script() {
  local env_prefix
  env_prefix="$(printf 'NODE_NAME=%q ROLE=%q APP_ROLE=%q MAIN_SERVER_IP=%q NODE_IP=%q REMOTE_APP=%q PORT=%q REMOTE_NODE_IPS=%q INSTALL_SERVICE=%q START_AFTER_DEPLOY=%q SKIP_SETUP=%q ' \
    "$NODE_NAME" "$ROLE" "$APP_ROLE" "$MAIN_SERVER_IP" "$NODE_IP" "$REMOTE_APP" "$PORT" "$REMOTE_NODE_IPS_DEFAULT" "$INSTALL_SERVICE" "$START_AFTER_DEPLOY" "$SKIP_SETUP")"
  ssh "${SSH_OPTS[@]}" "${SSH_USER}@${NODE_IP}" "${env_prefix} bash -s"
}

echo "============================================================"
echo " ADM FireNode Raspberry Pi Deployment"
echo " Target: ${NODE_NAME} (${NODE_IP})"
echo " Deployment role: ${ROLE}"
echo " App role: ${APP_ROLE}"
echo " Main server IP: ${MAIN_SERVER_IP}"
echo " App path on RPi: ${REMOTE_APP}"
echo " Simulation mode: enabled"
echo " Manual start default: enabled"
echo "============================================================"

echo "[1/5] Preparing remote folder and rsync support..."
ssh_remote "mkdir -p '$(dirname "$REMOTE_APP")' && if ! command -v rsync >/dev/null 2>&1; then sudo apt-get update && sudo apt-get install -y rsync; fi"

echo "[2/5] Deploying Raspberry Pi app files..."
RSYNC_SSH="ssh -i ${SSH_KEY} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
rsync -az --delete \
  -e "$RSYNC_SSH" \
  --exclude 'venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.DS_Store' \
  --exclude 'logs/' \
  --exclude 'media/' \
  "${REPO_ROOT}/${APP_REL}/" \
  "${SSH_USER}@${NODE_IP}:${REMOTE_APP}/"

echo "[3/5] Installing dependencies and configuring node..."
ssh_remote_script <<'REMOTE'
set -euo pipefail

cd "$REMOTE_APP"
chmod +x setup.sh run.sh check_mic.sh camera_test.py install_service.sh uninstall_service.sh || true
mkdir -p logs

if [ "$SKIP_SETUP" != "1" ]; then
  echo "Running app setup in manual-start mode..."
  ./setup.sh

  if [ -x "$REMOTE_APP/venv/bin/pip" ]; then
    echo "Installing Python requirements from requirements.txt..."
    "$REMOTE_APP/venv/bin/pip" install --no-cache-dir --prefer-binary -r "$REMOTE_APP/requirements.txt"
  fi
else
  echo "Skipping setup as requested."
fi

echo "Writing simulation deployment config..."
PYTHON_BIN="$REMOTE_APP/venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="python3"
fi

"$PYTHON_BIN" - "$REMOTE_APP/config.json" <<'PY'
import json
import os
import sys
from datetime import datetime

config_path = sys.argv[1]
node_name = os.environ["NODE_NAME"]
role = os.environ["ROLE"]
app_role = os.environ["APP_ROLE"]
node_ip = os.environ["NODE_IP"]
main_server_ip = os.environ["MAIN_SERVER_IP"]
port = int(os.environ["PORT"])
remote_node_ips = [x.strip() for x in os.environ.get("REMOTE_NODE_IPS", "").split(",") if x.strip()]

try:
    with open(config_path, "r", encoding="utf-8") as fh:
        config = json.load(fh)
except Exception:
    config = {}

config.update({
    "role": role,
    "app_role": app_role,
    "operation_mode": "simulation",
    "host": "0.0.0.0",
    "port": port,
    "node_name": node_name,
    "node_ip": node_ip,
    "main_server_ip": main_server_ip,
    "deployment_mode": "simulation",
    "deployment_updated_at": datetime.now().isoformat(timespec="seconds"),
    "selected_esp32_ip": "",
    "lora_enabled": True,
    "lora_sim_interval_sec": 5,
    "camera_enabled": True,
    "camera_device_index": 0,
    "camera_device_indexes": [0],
    "camera_backend": "V4L2",
    "camera_fourcc": "MJPG",
    "camera_open_warmup_frames": 5,
    "camera_retry_on_failed_read": True,
    "auto_start": False,
    "event_recording_enabled": True,
})

if app_role == "server":
    config.update({
        "remote_node_ips": remote_node_ips,
        "remote_node_count": 3,
        "thermal_enabled": True,
        "thermal_simulation": True,
    })
else:
    config.update({
        "remote_node_ips": [],
        "remote_node_count": 3,
        "thermal_enabled": False,
        "thermal_simulation": True,
    })

with open(config_path, "w", encoding="utf-8") as fh:
    json.dump(config, fh, indent=2)
    fh.write("\n")

print(f"Configured {node_name} as {role} in simulation mode.")
PY

cat > "$REMOTE_APP/.deployment.env" <<EOF
ADM_FIRE_NODE_NAME=$NODE_NAME
ADM_FIRE_NODE_IP=$NODE_IP
ADM_FIRE_ROLE=$ROLE
ADM_FIRE_APP_ROLE=$APP_ROLE
ADM_FIRE_MAIN_SERVER_IP=$MAIN_SERVER_IP
ADM_FIRE_APP_DIR=$REMOTE_APP
ADM_FIRE_PORT=$PORT
ADM_FIRE_MODE=simulation
EOF

echo "Creating optional systemd service file..."
sudo tee /etc/systemd/system/firenode-rpi.service >/dev/null <<EOF
[Unit]
Description=ADM FireNode RPi Web App (${NODE_NAME})
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${REMOTE_APP}
ExecStart=/bin/bash ${REMOTE_APP}/run.sh
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload

if [ "$INSTALL_SERVICE" = "1" ]; then
  echo "Enabling and starting optional systemd service..."
  sudo systemctl enable firenode-rpi.service
  sudo systemctl restart firenode-rpi.service
else
  echo "Service file created but not enabled. Manual start remains the default."
  echo "To enable later: sudo systemctl enable --now firenode-rpi.service"
fi

if [ "$START_AFTER_DEPLOY" = "1" ]; then
  echo "Starting app once with nohup..."
  pkill -f "${REMOTE_APP}/app.py" 2>/dev/null || true
  nohup "$REMOTE_APP/run.sh" > "$REMOTE_APP/logs/manual-run.log" 2>&1 &
  sleep 2
fi
REMOTE

echo "[4/5] Deployment commands for this Raspberry Pi:"
cat <<EOF

Manual start:
  ssh -i "${SSH_KEY}" ${SSH_USER}@${NODE_IP}
  cd "${REMOTE_APP}"
  ./run.sh

Optional service controls:
  ssh -i "${SSH_KEY}" ${SSH_USER}@${NODE_IP} 'sudo systemctl status firenode-rpi --no-pager'
  ssh -i "${SSH_KEY}" ${SSH_USER}@${NODE_IP} 'sudo systemctl enable --now firenode-rpi'
  ssh -i "${SSH_KEY}" ${SSH_USER}@${NODE_IP} 'sudo systemctl disable --now firenode-rpi'

Browser/API checks after the app is running:
  open http://${NODE_IP}:${PORT}
  curl http://${NODE_IP}:${PORT}/api/status
  curl http://${NODE_IP}:${PORT}/api/config
  curl http://${NODE_IP}:${PORT}/api/node-data
  curl http://${NODE_IP}:${PORT}/api/lora/status
  curl -I --max-time 5 http://${NODE_IP}:${PORT}/video_feed
EOF

if [ "$APP_ROLE" = "server" ]; then
  cat <<EOF
  curl http://${NODE_IP}:${PORT}/api/server-dashboard
  curl --output /tmp/firenode-thermal.png http://${NODE_IP}:${PORT}/thermal.png
EOF
fi

if [ "$VALIDATE_AFTER_DEPLOY" = "1" ]; then
  echo "[5/5] Running lightweight validation checks..."
  ssh_remote "echo 'SSH connectivity OK on ${NODE_NAME}'; command -v python3; command -v rsync; dpkg -s python3-venv python3-flask python3-requests curl >/dev/null; PY='${REMOTE_APP}/venv/bin/python'; [ -x \"\$PY\" ] || PY=python3; test -x '${REMOTE_APP}/run.sh' && test -f '${REMOTE_APP}/config.json' && \"\$PY\" -m py_compile '${REMOTE_APP}/app.py'"
  ssh_remote "sudo systemctl status firenode-rpi --no-pager || true"
  if curl --fail --silent --max-time 3 "http://${NODE_IP}:${PORT}/api/status" >/dev/null; then
    echo "API status check passed: http://${NODE_IP}:${PORT}/api/status"
  else
    echo "API status check skipped/failed. Start manually with ./run.sh, then rerun the curl checks."
  fi
else
  echo "[5/5] Validation not run. Use --validate after starting the app, or run the printed commands manually."
fi

echo ""
echo "Deployment complete for ${NODE_NAME} (${NODE_IP})."
