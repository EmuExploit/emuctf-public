#!/bin/sh
set -eu

: "${POSTGRES_USER:=ddgu}"
: "${POSTGRES_DB:=ddgdb}"
: "${POSTGRES_PASSWORD:=ddgpass}"
export POSTGRES_USER POSTGRES_DB POSTGRES_PASSWORD

FLAG_VALUE="${FLAG:-${flag:-}}"
unset FLAG flag 2>/dev/null || true

if [ -z "$FLAG_VALUE" ]; then
    echo "entrypoint: warning: no FLAG provided, loading placeholder" >&2
    FLAG_VALUE="EMU{no_flag_was_set}"
fi

docker-entrypoint.sh postgres -c listen_addresses=127.0.0.1 &
PG_PID=$!

echo "entrypoint: waiting for Postgres..." >&2
until pg_isready -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
    if [ ! -d "/proc/$PG_PID" ]; then
        echo "entrypoint: Postgres exited before becoming ready" >&2
        exit 1
    fi
    sleep 1
done

escaped_flag=$(printf '%s' "$FLAG_VALUE" | sed "s/'/''/g")
PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null <<SQL
CREATE TABLE IF NOT EXISTS flag (flag text NOT NULL);
TRUNCATE flag;
INSERT INTO flag (flag) VALUES ('${escaped_flag}');
SQL

FLAG_VALUE=""
escaped_flag=""
unset FLAG_VALUE escaped_flag

export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:5432/${POSTGRES_DB}?sslmode=disable"
export HOME=/tmp

echo "entrypoint: starting duckduckgo" >&2
cd /app
exec /app/duckduckgo
