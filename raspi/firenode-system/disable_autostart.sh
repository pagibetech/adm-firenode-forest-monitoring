#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
./uninstall_service.sh
echo "Autostart disabled. Start manually with: ./run.sh"
