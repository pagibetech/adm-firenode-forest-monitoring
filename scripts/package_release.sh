#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/dist"
STAMP="$(date +%Y%m%d-%H%M%S)"
COMMIT="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo nogit)"
NAME="adm-firenode-${COMMIT}-${STAMP}.zip"

mkdir -p "$OUT_DIR"

if git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$ROOT_DIR" archive --format=zip --output="$OUT_DIR/$NAME" HEAD
else
  echo "This script must be run from a Git-tracked project." >&2
  exit 1
fi

echo "$OUT_DIR/$NAME"
