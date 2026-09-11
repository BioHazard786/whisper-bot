#!/bin/sh
set -e

# Resolve target SQLite directory from environment or use default
DB_PATH="${SQLITE_DB_PATH:-/app/data/whispers.db}"
DB_DIR="$(dirname "$DB_PATH")"

# If running as root (default in Docker), fix volume permissions and drop privileges
if [ "$(id -u)" = "0" ]; then
    if [ -n "$DB_DIR" ]; then
        mkdir -p "$DB_DIR"
        chown -R appuser:appgroup "$DB_DIR"
        chmod 770 "$DB_DIR"
    fi
    exec su-exec appuser "$@"
fi

# If already running as a non-root user (e.g. docker run --user)
exec "$@"
