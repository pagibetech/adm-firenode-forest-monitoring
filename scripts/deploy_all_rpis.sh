#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${REPO_ROOT}/logs"

SSH_KEY="${ADM_FIRE_SSH_KEY:-${HOME}/admfire}"
SSH_USER="${ADM_FIRE_SSH_USER:-betech}"
MAIN_SERVER_IP="${ADM_FIRE_MAIN_SERVER_IP:-192.168.9.51}"
NODE_1_IP="${ADM_FIRE_NODE_1_IP:-192.168.9.52}"
NODE_2_IP="${ADM_FIRE_NODE_2_IP:-192.168.9.53}"
NODE_3_IP="${ADM_FIRE_NODE_3_IP:-192.168.9.54}"

SEQUENTIAL="0"
TARGET_IP=""
DEPLOY_ARGS=()

usage() {
  cat <<EOF
Usage:
  $0 [options] [deploy-node-options]

Fleet options:
  --parallel          Deploy all selected RPis in parallel. Default.
  --sequential        Deploy one RPi at a time.
  --target <ip>       Deploy only one target IP.
  -h, --help          Show this help.

Options passed through to deploy_node.sh:
  --install-service   Install, enable, and start optional systemd service.
  --start             Start the app once with nohup after deployment.
  --validate          Run lightweight checks after deployment.
  --skip-setup        Copy/configure only; skip apt/venv dependency setup.

Targets:
  ${MAIN_SERVER_IP} = main_server
  ${NODE_1_IP} = node_01
  ${NODE_2_IP} = node_02
  ${NODE_3_IP} = node_03

Examples:
  $0
  $0 --sequential
  $0 --target 192.168.9.52
  $0 --target 192.168.9.51 --validate
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --parallel)
      SEQUENTIAL="0"
      shift
      ;;
    --sequential)
      SEQUENTIAL="1"
      shift
      ;;
    --target)
      TARGET_IP="${2:-}"
      if [ -z "$TARGET_IP" ]; then
        echo "--target requires an IP address." >&2
        exit 2
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      DEPLOY_ARGS+=("$1")
      shift
      ;;
  esac
done

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key not found: $SSH_KEY" >&2
  exit 1
fi

mkdir -p "$LOG_DIR"

TARGETS=(
  "main_server|${MAIN_SERVER_IP}|main_server"
  "node_01|${NODE_1_IP}|node_01"
  "node_02|${NODE_2_IP}|node_02"
  "node_03|${NODE_3_IP}|node_03"
)

SELECTED=()
for target in "${TARGETS[@]}"; do
  IFS='|' read -r name ip role <<<"$target"
  if [ -n "$TARGET_IP" ] && [ "$TARGET_IP" != "$ip" ]; then
    continue
  fi
  SELECTED+=("$target")
done

if [ "${#SELECTED[@]}" -eq 0 ]; then
  echo "No matching target for IP: ${TARGET_IP}" >&2
  usage
  exit 2
fi

run_one() {
  local name="$1"
  local ip="$2"
  local role="$3"
  local log_file="${LOG_DIR}/deploy_${ip}.log"

  {
    echo "============================================================"
    echo "ADM FireNode deployment log"
    echo "Target: ${name} (${ip})"
    echo "Role: ${role}"
    echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "============================================================"
    "${SCRIPT_DIR}/deploy_node.sh" "$name" "$ip" "$role" "$MAIN_SERVER_IP" "${DEPLOY_ARGS[@]}"
    echo "============================================================"
    echo "Finished: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Result: SUCCESS"
    echo "============================================================"
  } >"$log_file" 2>&1
}

print_header() {
  echo "Deploying ADM FireNode Raspberry Pi fleet in simulation mode..."
  echo "Mode: $([ "$SEQUENTIAL" = "1" ] && echo sequential || echo parallel)"
  echo "SSH user: ${SSH_USER}"
  echo "SSH key: ${SSH_KEY}"
  echo "Logs: ${LOG_DIR}/deploy_<ip>.log"
  echo ""
  for target in "${SELECTED[@]}"; do
    IFS='|' read -r name ip role <<<"$target"
    echo "- ${ip} = ${name}"
  done
  echo ""
}

print_summary() {
  echo ""
  echo "Deployment summary:"
  local failures=0
  for target in "${SELECTED[@]}"; do
    IFS='|' read -r name ip role <<<"$target"
    local log_file="${LOG_DIR}/deploy_${ip}.log"
    local status_var="STATUS_${ip//./_}"
    local status="${!status_var:-1}"
    if [ "$status" = "0" ]; then
      echo "  PASS ${ip} ${name} (${log_file})"
    else
      echo "  FAIL ${ip} ${name} (${log_file})"
      failures=$((failures + 1))
    fi
  done
  echo ""
  echo "Manual start example:"
  echo "  ssh -i \"${SSH_KEY}\" ${SSH_USER}@${MAIN_SERVER_IP} 'cd /home/${SSH_USER}/admfire/raspi/firenode-system && ./run.sh'"
  echo ""
  echo "Main dashboard after manual start:"
  echo "  http://${MAIN_SERVER_IP}:8090"
  return "$failures"
}

print_header

if [ "$SEQUENTIAL" = "1" ]; then
  for target in "${SELECTED[@]}"; do
    IFS='|' read -r name ip role <<<"$target"
    echo "Deploying ${name} (${ip})..."
    if run_one "$name" "$ip" "$role"; then
      declare "STATUS_${ip//./_}=0"
      echo "PASS ${ip}. Log: ${LOG_DIR}/deploy_${ip}.log"
    else
      declare "STATUS_${ip//./_}=1"
      echo "FAIL ${ip}. Log: ${LOG_DIR}/deploy_${ip}.log"
    fi
  done
else
  PIDS=()
  PID_TARGETS=()
  for target in "${SELECTED[@]}"; do
    IFS='|' read -r name ip role <<<"$target"
    echo "Starting ${name} (${ip}) in background..."
    run_one "$name" "$ip" "$role" &
    PIDS+=("$!")
    PID_TARGETS+=("$target")
  done

  for idx in "${!PIDS[@]}"; do
    pid="${PIDS[$idx]}"
    target="${PID_TARGETS[$idx]}"
    IFS='|' read -r name ip role <<<"$target"
    if wait "$pid"; then
      declare "STATUS_${ip//./_}=0"
      echo "PASS ${ip}. Log: ${LOG_DIR}/deploy_${ip}.log"
    else
      declare "STATUS_${ip//./_}=1"
      echo "FAIL ${ip}. Log: ${LOG_DIR}/deploy_${ip}.log"
    fi
  done
fi

if print_summary; then
  exit 0
else
  exit 1
fi
