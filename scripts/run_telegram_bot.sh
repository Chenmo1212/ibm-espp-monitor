#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

export PYTHONPATH="src:${PYTHONPATH:-}"

exec python3 -m ibm_espp_monitor --bot
