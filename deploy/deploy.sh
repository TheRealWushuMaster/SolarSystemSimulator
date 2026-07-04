#!/usr/bin/env bash
# Redeploy Solara on the VPS: pull latest code, sync backend deps, rebuild
# the frontend, restart the backend service. Run from anywhere; it locates
# the repo root relative to its own location.
#
# Usage: deploy/deploy.sh [--no-pull]
#
# Assumes the one-time setup from the deployment runbook is already done:
# the solara-backend systemd unit is installed, de440t.bsp is in place, and
# the Nginx site is configured. This script does NOT touch systemd unit
# files or the Nginx config -- re-run the relevant `sudo cp` steps by hand
# if those changed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="solara-backend"
PULL=true

for arg in "$@"; do
    case "$arg" in
        --no-pull) PULL=false ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

cd "$REPO_ROOT"

if [ "$PULL" = true ]; then
    echo "==> Pulling latest code"
    git pull --ff-only
fi

echo "==> Syncing backend dependencies"
uv sync --group server

echo "==> Building frontend"
(cd web && npm install && npm run build)

echo "==> Restarting $SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager -l

echo "==> Reloading Nginx (picks up any static asset changes)"
sudo systemctl reload nginx

echo "==> Health check"
if curl -sf http://127.0.0.1:8000/api/bodies > /dev/null; then
    echo "OK: backend responding on 127.0.0.1:8000"
else
    echo "WARNING: backend did not respond on 127.0.0.1:8000 -- check 'journalctl -u $SERVICE_NAME -n 50'" >&2
    exit 1
fi

echo "==> Done"
