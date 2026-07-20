#!/usr/bin/env bash
# Start the FastAPI backend from a project virtual environment.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
HOST="127.0.0.1"
PORT="8000"
RELOAD=0

usage() {
  cat <<'EOF'
Usage: ./run_backend.sh [--host HOST] [--port PORT] [--reload]

Defaults to http://127.0.0.1:8000. The script uses backend/.venv when
available, then backend/venv, then python3. It does not force Hugging Face
offline mode; set HF_HUB_OFFLINE=1 yourself only after caching model weights.
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
    --reload)
      RELOAD=1
      shift
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

PYTHON=""
PYTHON_CANDIDATES=(
  "$BACKEND_DIR/.venv/bin/python"
  "$BACKEND_DIR/venv/bin/python"
)
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CANDIDATES+=("$(command -v python3)")
fi

# A stale or partially installed virtualenv must not shadow a working fallback.
# Select the first candidate that can import the minimum server runtime.
for candidate in "${PYTHON_CANDIDATES[@]}"; do
  if [[ -x "$candidate" ]] && "$candidate" -c 'import uvicorn, fastapi, pydantic, dotenv' >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  printf '%s\n' 'No usable backend Python environment was found.' >&2
  printf '%s\n' 'Install backend requirements into backend/.venv (see README.md).' >&2
  exit 1
fi

cd "$BACKEND_DIR"
ARGS=(app.main:app --host "$HOST" --port "$PORT" --log-level info)
if (( RELOAD == 1 )); then
  ARGS+=(--reload)
fi

# Uvicorn reads the env file before importing app.main. This keeps import-time
# settings reproducible. No Hugging Face offline flag is forced.
if [[ -f .env ]]; then
  exec "$PYTHON" -m uvicorn "${ARGS[@]}" --env-file .env
else
  exec "$PYTHON" -m uvicorn "${ARGS[@]}"
fi
