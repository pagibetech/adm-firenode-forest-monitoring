#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/raspi/firenode-system"

cd "$APP_DIR"
python3 -m unittest discover -s tests -p "test_*.py"
