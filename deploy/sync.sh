#!/usr/bin/env bash
# Push the local working tree to the VPS. Code lives locally; nothing is built here.
#   usage: bash deploy/sync.sh
set -euo pipefail

VPS_HOST="${VPS_HOST:-root@169.58.38.11}"
VPS_KEY="${VPS_KEY:-${USERPROFILE:-$HOME}/.ssh/elitetek-academy}"
REMOTE_DIR="${REMOTE_DIR:-/root/rakib/src}"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ssh -i "$VPS_KEY" -o StrictHostKeyChecking=no "$VPS_HOST" "mkdir -p $REMOTE_DIR"

tar -czf - -C "$LOCAL_DIR" \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    --exclude='.ruff_cache' \
    --exclude='dist' \
    . \
  | ssh -i "$VPS_KEY" -o StrictHostKeyChecking=no "$VPS_HOST" \
        "tar -xzf - -C $REMOTE_DIR"

echo "synced -> $VPS_HOST:$REMOTE_DIR"
