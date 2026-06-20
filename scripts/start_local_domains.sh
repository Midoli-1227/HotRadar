#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT/frontend"
JPNOTE_ROOT="${HOTRADAR_JP_NOTEBOOK_ROOT:-/Users/lanyangyang/Documents/Japanese_notebook_codex}"
HOTRADAR_DOMAIN="${HOTRADAR_LOCAL_DOMAIN:-hotradar.test}"
JPNOTE_DOMAIN="${JPNOTE_LOCAL_DOMAIN:-jpnote.test}"
PORT="${LOCAL_DOMAIN_PORT:-8088}"

if ! grep -qE "(^|[[:space:]])${HOTRADAR_DOMAIN}([[:space:]]|$)" /etc/hosts ||
  ! grep -qE "(^|[[:space:]])${JPNOTE_DOMAIN}([[:space:]]|$)" /etc/hosts; then
  cat <<EOF
Missing local domain entries in /etc/hosts.

Run this once in Terminal, then start this script again:

  sudo sh -c 'printf "\\n127.0.0.1 ${HOTRADAR_DOMAIN} ${JPNOTE_DOMAIN}\\n" >> /etc/hosts'

EOF
  exit 1
fi

if [[ ! -d "$JPNOTE_ROOT" ]]; then
  echo "Japanese Notebook folder not found: $JPNOTE_ROOT" >&2
  exit 1
fi

if [[ -n "${NPM_BIN:-}" ]]; then
  NPM_BIN="$NPM_BIN"
elif [[ -x /opt/homebrew/bin/npm ]]; then
  NPM_BIN="/opt/homebrew/bin/npm"
else
  NPM_BIN="npm"
fi

echo "Building HotRadar frontend..."
(cd "$FRONTEND_DIR" && "$NPM_BIN" run build)

PYTHON_BIN="${HOTRADAR_PYTHON:-$ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  cat <<EOF
HotRadar Python environment was not found:

  $PYTHON_BIN

Create it once with:

  cd "$ROOT"
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt

EOF
  exit 1
fi

if ! curl -fsS "http://127.0.0.1:8000/api/dashboard" >/dev/null 2>&1; then
  echo "Starting HotRadar backend on http://127.0.0.1:8000..."
  (cd "$ROOT" && "$PYTHON_BIN" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000) &
  BACKEND_PID=$!
  trap 'kill "$BACKEND_PID" >/dev/null 2>&1 || true' EXIT
  sleep 2
else
  echo "HotRadar backend is already running."
fi

cat <<EOF

Local domains are ready:
  HotRadar:          http://${HOTRADAR_DOMAIN}:${PORT}
  Japanese Notebook: http://${JPNOTE_DOMAIN}:${PORT}

Press Ctrl+C to stop the local domain gateway.

EOF

exec "$PYTHON_BIN" "$ROOT/scripts/local_domains.py" --port "$PORT"
