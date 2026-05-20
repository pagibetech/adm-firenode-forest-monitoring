#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MAIN_SERVER_IP="${ADM_FIRE_MAIN_SERVER_IP:-192.168.9.51}"
NODE_1_IP="${ADM_FIRE_NODE_1_IP:-192.168.9.52}"
NODE_2_IP="${ADM_FIRE_NODE_2_IP:-192.168.9.53}"
NODE_3_IP="${ADM_FIRE_NODE_3_IP:-192.168.9.54}"

echo "Deploying ADM FireNode Raspberry Pi fleet in simulation mode..."
echo "Main Server: ${MAIN_SERVER_IP}"
echo "Node 1:      ${NODE_1_IP}"
echo "Node 2:      ${NODE_2_IP}"
echo "Node 3:      ${NODE_3_IP}"
echo ""

"${SCRIPT_DIR}/deploy_main_server.sh" "$@"
"${SCRIPT_DIR}/deploy_node.sh" node-01 "${NODE_1_IP}" node "${MAIN_SERVER_IP}" "$@"
"${SCRIPT_DIR}/deploy_node.sh" node-02 "${NODE_2_IP}" node "${MAIN_SERVER_IP}" "$@"
"${SCRIPT_DIR}/deploy_node.sh" node-03 "${NODE_3_IP}" node "${MAIN_SERVER_IP}" "$@"

cat <<EOF

All Raspberry Pi deployment commands completed.

Manual start on each RPi:
  ssh -i "\${ADM_FIRE_SSH_KEY:-\$HOME/admfire}" betech@${MAIN_SERVER_IP} 'cd /home/betech/admfire/raspi/firenode-system && ./run.sh'
  ssh -i "\${ADM_FIRE_SSH_KEY:-\$HOME/admfire}" betech@${NODE_1_IP} 'cd /home/betech/admfire/raspi/firenode-system && ./run.sh'
  ssh -i "\${ADM_FIRE_SSH_KEY:-\$HOME/admfire}" betech@${NODE_2_IP} 'cd /home/betech/admfire/raspi/firenode-system && ./run.sh'
  ssh -i "\${ADM_FIRE_SSH_KEY:-\$HOME/admfire}" betech@${NODE_3_IP} 'cd /home/betech/admfire/raspi/firenode-system && ./run.sh'

Main dashboard:
  http://${MAIN_SERVER_IP}:8090

Main server API checks:
  curl http://${MAIN_SERVER_IP}:8090/api/status
  curl http://${MAIN_SERVER_IP}:8090/api/server-dashboard
  curl http://${MAIN_SERVER_IP}:8090/api/lora/status
EOF
