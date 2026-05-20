#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MAIN_SERVER_IP="${ADM_FIRE_MAIN_SERVER_IP:-192.168.9.51}"

exec "${SCRIPT_DIR}/deploy_node.sh" \
  node-main-center \
  "${MAIN_SERVER_IP}" \
  server \
  "${MAIN_SERVER_IP}" \
  "$@"
