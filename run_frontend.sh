#!/usr/bin/env bash
# Start the Vite development server on localhost by default.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
HOST="127.0.0.1"
PORT="5173"

usage() {
  cat <<'EOF'
Usage: ./run_frontend.sh [--host HOST] [--port PORT]

Defaults to http://127.0.0.1:5173. Pass --host 0.0.0.0 only when you
intentionally want to expose the development server to other hosts.
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --host)
      (( $# >= 2 )) || { printf '%s\n' '--host requires a value' >&2; exit 2; }
      HOST="$2"
      shift 2
      ;;
    --port)
      (( $# >= 2 )) || { printf '%s\n' '--port requires a value' >&2; exit 2; }
      PORT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

command -v npm >/dev/null 2>&1 || { printf '%s\n' 'npm was not found' >&2; exit 1; }
cd "$FRONTEND_DIR"
exec npm run dev -- --host "$HOST" --port "$PORT"
