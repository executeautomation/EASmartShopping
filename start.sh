#!/usr/bin/env bash
# start.sh — starts both the backend (FastAPI) and frontend (Next.js)
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

BACKEND_PORT=8000
FRONTEND_PORT=3000

# ── colours ─────────────────────────────────────────────────────────────────
GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"; RESET="\033[0m"

log()  { echo -e "${GREEN}[start]${RESET} $*"; }
warn() { echo -e "${YELLOW}[warn]${RESET}  $*"; }
die()  { echo -e "${RED}[error]${RESET} $*" >&2; exit 1; }

# ── kill any stale processes on the ports ───────────────────────────────────
kill_port() {
  local port=$1
  local pids
  pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    warn "Port $port in use — stopping PIDs: $(echo $pids | tr '\n' ' ')"
    echo "$pids" | while read -r pid; do
      kill "$pid" 2>/dev/null || true
    done
    sleep 1
  fi
}

kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

# ── backend ──────────────────────────────────────────────────────────────────
log "Starting backend (FastAPI) on http://localhost:$BACKEND_PORT ..."

VENV="$BACKEND/venv/bin/activate"
[ -f "$VENV" ] || die "Python venv not found at $VENV — run: cd backend && python -m venv venv && pip install -r requirements.txt"

(
  cd "$BACKEND"
  # shellcheck source=/dev/null
  source "$VENV"
  uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT 2>&1 | sed "s/^/  [backend] /"
) &
BACKEND_PID=$!

# ── wait for backend to be ready ────────────────────────────────────────────
log "Waiting for backend..."
for i in $(seq 1 15); do
  if curl -s "http://localhost:$BACKEND_PORT/api/products" -o /dev/null; then
    log "Backend ready ✅"
    break
  fi
  sleep 1
  if [ "$i" -eq 15 ]; then
    die "Backend didn't start in time. Check logs above."
  fi
done

# ── frontend ──────────────────────────────────────────────────────────────────
log "Starting frontend (Next.js) on http://localhost:$FRONTEND_PORT ..."

[ -d "$FRONTEND/node_modules" ] || die "node_modules missing — run: cd frontend && npm install"

(
  cd "$FRONTEND"
  npm run dev 2>&1 | sed "s/^/  [frontend] /"
) &
FRONTEND_PID=$!

# ── wait for frontend to be ready ───────────────────────────────────────────
log "Waiting for frontend..."
for i in $(seq 1 20); do
  if curl -s "http://localhost:$FRONTEND_PORT" -o /dev/null; then
    log "Frontend ready ✅"
    break
  fi
  sleep 1
  if [ "$i" -eq 20 ]; then
    die "Frontend didn't start in time. Check logs above."
  fi
done

# ── summary ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}  App is running!${RESET}"
echo -e "  Frontend  →  http://localhost:$FRONTEND_PORT"
echo -e "  Backend   →  http://localhost:$BACKEND_PORT"
echo -e "  API docs  →  http://localhost:$BACKEND_PORT/docs"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "  Press Ctrl+C to stop both servers"
echo ""

# ── trap Ctrl+C to kill both ─────────────────────────────────────────────────
cleanup() {
  echo ""
  log "Stopping servers..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
  log "Done."
}
trap cleanup INT TERM

wait $BACKEND_PID $FRONTEND_PID
