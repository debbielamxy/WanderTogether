#!/usr/bin/env bash
set -euo pipefail

# start.sh — stop any running app and start a new one
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

PIDFILE=".app.pid"
LOGFILE="app.log"

echo "Stopping any process listening on port 5001..."
PIDS=$(lsof -t -iTCP:5001 -sTCP:LISTEN || true)
if [ -n "$PIDS" ]; then
  echo "Killing: $PIDS"
  kill $PIDS || true
fi

if [ -f "$PIDFILE" ]; then
  OLD_PID=$(cat "$PIDFILE")
  if ps -p $OLD_PID > /dev/null 2>&1; then
    echo "Killing old PID $OLD_PID"
    kill $OLD_PID || true
  fi
  rm -f "$PIDFILE"
fi

echo "Starting app..."
# Start the app in background and redirect output to logfile
nohup python3 app.py >> "$LOGFILE" 2>&1 &
NEW_PID=$!
echo $NEW_PID > "$PIDFILE"
echo "App started with PID $NEW_PID — logs: $LOGFILE"

echo "Waiting 1s for server to come up..."
sleep 1
MAX_WAIT=10
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
  if curl -sSf "http://127.0.0.1:5001/status" > /dev/null; then
    echo "Server is responding at http://127.0.0.1:5001/"
    # Open the browser on macOS
    if command -v open >/dev/null 2>&1; then
      open "http://127.0.0.1:5001/"
    fi
    exit 0
  fi
  sleep 1
  WAITED=$((WAITED+1))
done

echo "Server did not respond within ${MAX_WAIT}s. Check $LOGFILE for errors."

exit 0
