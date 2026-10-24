#!/bin/sh
# Backend (stdlib unittest; pytest also works) then frontend, if node_modules exists.
set -e
cd "$(dirname "$0")/../backend"
python3 -m unittest discover -s app/tests -t . -v
if [ -d ../frontend/node_modules ]; then (cd ../frontend && npm test); else echo "frontend deps not installed: skipping Vitest"; fi
