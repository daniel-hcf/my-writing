#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PID_FILE="$SCRIPT_DIR/.app.pid"
LOG_FILE="$SCRIPT_DIR/app.log"

check_venv() {
    if [ ! -f "$VENV/bin/activate" ]; then
        echo "Error: .venv not found. Run:"
        echo "  python -m venv .venv && .venv/bin/pip install -r requirements.txt"
        exit 1
    fi
}

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Already running (PID: $(cat "$PID_FILE"))"
        exit 1
    fi
    check_venv
    source "$VENV/bin/activate"
    nohup python -m my_writing >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "Started (PID: $!, log: app.log)"
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Not running (no PID file)"
        exit 1
    fi
    PID=$(cat "$PID_FILE")
    if kill "$PID" 2>/dev/null; then
        rm "$PID_FILE"
        echo "Stopped (PID: $PID)"
    else
        rm "$PID_FILE"
        echo "Process $PID not found, removed stale PID file"
    fi
}

restart() {
    stop 2>/dev/null || true
    sleep 1
    start
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Running (PID: $(cat "$PID_FILE"))"
    else
        [ -f "$PID_FILE" ] && rm "$PID_FILE"
        echo "Not running"
    fi
}

case "$1" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    *)       echo "Usage: $0 {start|stop|restart|status}"; exit 1 ;;
esac
