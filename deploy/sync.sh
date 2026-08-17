#!/usr/bin/env bash
# Push the local working tree to the VPS. Code lives locally; nothing is built here.
#   usage: bash deploy/sync.sh
set -euo pipefail

# Renseigner VPS_HOST et VPS_KEY dans l'environnement : l'adresse du
# serveur et le nom du fichier de cle n'ont pas a etre versionnes.
VPS_HOST="${VPS_HOST:?definir VPS_HOST, ex. root@203.0.113.10}"
VPS_KEY="${VPS_KEY:?definir VPS_KEY, chemin de la cle SSH}"
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
