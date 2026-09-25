#!/bin/bash
set -eo pipefail

# Configuration defaults
export CDP_PORT="${CDP_PORT:-9222}"
export CDP_HOST="${CDP_HOST:-127.0.0.1}"
export CHROME_CDP_URL="${CHROME_CDP_URL:-http://$CDP_HOST:$CDP_PORT}"
export CHROME_USER_DATA_DIR="${CHROME_USER_DATA_DIR:-/data/chrome-profile}"
export CHROME_HEADLESS="${CHROME_HEADLESS:-new}"
export CHROME_STARTUP_URL="${CHROME_STARTUP_URL:-about:blank}"
export START_BROWSER="${START_BROWSER:-true}"

CHROME_PID=""
SCRAPER_PID=""

# Graceful shutdown handler
cleanup() {
    echo "[ENTRYPOINT] Received shutdown signal. Terminating processes gracefully..."
    if [ -n "$SCRAPER_PID" ] && kill -0 "$SCRAPER_PID" 2>/dev/null; then
        echo "[ENTRYPOINT] Stopping scraper (PID: $SCRAPER_PID)..."
        kill -TERM "$SCRAPER_PID" 2>/dev/null || true
        wait "$SCRAPER_PID" 2>/dev/null || true
    fi

    if [ -n "$CHROME_PID" ] && kill -0 "$CHROME_PID" 2>/dev/null; then
        echo "[ENTRYPOINT] Stopping Chrome (PID: $CHROME_PID)..."
        kill -TERM "$CHROME_PID" 2>/dev/null || true
        wait "$CHROME_PID" 2>/dev/null || true
    fi
    echo "[ENTRYPOINT] Shutdown complete."
    exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT SIGHUP

if [ "$START_BROWSER" = "true" ] || [ "$START_BROWSER" = "1" ]; then
    # Ensure profile directory exists
    mkdir -p "$CHROME_USER_DATA_DIR"

    # Remove stale Chrome lock files from unclean shutdowns
    rm -f "$CHROME_USER_DATA_DIR/SingletonLock" \
          "$CHROME_USER_DATA_DIR/SingletonCookie" \
          "$CHROME_USER_DATA_DIR/SingletonSocket" 2>/dev/null || true

    # Locate Chrome / Chromium binary
    CHROME_BIN=$(which chromium || which chromium-browser || which google-chrome-stable || which google-chrome || true)
    if [ -z "$CHROME_BIN" ]; then
        echo "[ENTRYPOINT] ERROR: No Chromium / Chrome binary found on PATH!"
        exit 1
    fi

    CHROME_ARGS=(
        "--remote-debugging-port=${CDP_PORT}"
        "--remote-debugging-address=${CDP_HOST}"
        "--user-data-dir=${CHROME_USER_DATA_DIR}"
        "--no-sandbox"
        "--disable-setuid-sandbox"
        "--disable-dev-shm-usage"
        "--disable-gpu"
        "--no-first-run"
        "--no-default-browser-check"
        "--disable-background-networking"
        "--disable-default-apps"
    )

    if [ "$CHROME_HEADLESS" = "new" ] || [ "$CHROME_HEADLESS" = "true" ] || [ "$CHROME_HEADLESS" = "1" ]; then
        CHROME_ARGS+=("--headless=new")
    fi

    echo "[ENTRYPOINT] Starting $CHROME_BIN with CDP on $CDP_HOST:$CDP_PORT..."
    "$CHROME_BIN" "${CHROME_ARGS[@]}" "$CHROME_STARTUP_URL" > /tmp/chrome.log 2>&1 &
    CHROME_PID=$!

    # Wait for CDP endpoint readiness
    echo "[ENTRYPOINT] Waiting for Chrome CDP at http://${CDP_HOST}:${CDP_PORT}/json/version..."
    MAX_RETRIES=30
    RETRY_COUNT=0
    CDP_READY=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -sf "http://${CDP_HOST}:${CDP_PORT}/json/version" > /dev/null 2>&1; then
            CDP_READY=1
            break
        fi
        # Check if Chrome process died prematurely
        if ! kill -0 "$CHROME_PID" 2>/dev/null; then
            echo "[ENTRYPOINT] ERROR: Chrome process exited unexpectedly before CDP became ready."
            echo "[ENTRYPOINT] Chrome log output:"
            cat /tmp/chrome.log || true
            exit 1
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        sleep 1
    done

    if [ $CDP_READY -ne 1 ]; then
        echo "[ENTRYPOINT] ERROR: Chrome CDP failed to become ready after $MAX_RETRIES seconds."
        echo "[ENTRYPOINT] Chrome log output:"
        cat /tmp/chrome.log || true
        kill -9 "$CHROME_PID" 2>/dev/null || true
        exit 1
    fi

    echo "[ENTRYPOINT] Chrome CDP is healthy and ready on port $CDP_PORT."
fi

# Execute scraper command
echo "[ENTRYPOINT] Starting application: $@"
"$@" &
SCRAPER_PID=$!

# Wait for scraper process
wait "$SCRAPER_PID"
EXIT_CODE=$?

cleanup
exit $EXIT_CODE
