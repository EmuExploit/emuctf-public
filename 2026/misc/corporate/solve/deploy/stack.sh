#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

if compose_version=$(docker compose version --short 2>/dev/null); then
    compose_mode=plugin
    compose() { docker compose "$@"; }
elif compose_version=$(docker-compose version --short 2>/dev/null); then
    compose_mode=standalone
    compose() { docker-compose "$@"; }
else
    echo 'Install Docker Compose: either docker compose or docker-compose is required.' >&2
    exit 1
fi
case "$compose_version" in
    1.*|v1.*)
        echo 'Legacy Docker Compose v1 is unsupported; upgrade to modern Compose v2+.' >&2
        exit 1
        ;;
esac

monitor() {
    interval=${1:-15}
    case "$interval" in ''|*[!0-9]*) echo 'Interval must be an integer >= 5 seconds.' >&2; exit 1 ;; esac
    [ "$interval" -ge 5 ] || { echo 'Interval must be >= 5 seconds.' >&2; exit 1; }
    command -v python3 >/dev/null 2>&1 || { echo 'Monitor requires Python 3 (standard library only).' >&2; exit 1; }
    exec python3 monitor.py "$interval" "$compose_mode"
}

validate_config() {
    command -v python3 >/dev/null 2>&1 || { echo 'Configuration checks require Python 3.' >&2; exit 1; }
    compose config --format json | python3 -c '
import json, sys
from urllib.parse import urlsplit
services = json.load(sys.stdin)["services"]
public = services["frontend"]["environment"]
review = services["reviewer"]["environment"]
if public["SESSION_SECRET"] == review["SESSION_SECRET"]:
    sys.exit("REVIEW_SESSION_SECRET must differ from SESSION_SECRET.")
addresses = services["caddy"]["environment"]
urls = [urlsplit(addresses[key]) for key in ("SITE_ADDRESS", "REVIEW_SITE_ADDRESS", "UPLOAD_SITE_ADDRESS")]
if any(url.scheme not in ("http", "https") or not url.hostname for url in urls):
    sys.exit("SITE_ADDRESS, REVIEW_SITE_ADDRESS and UPLOAD_SITE_ADDRESS must be HTTP(S) URLs.")
if len({url.hostname for url in urls}) != len(urls):
    sys.exit("Website, reviewer and upload access require three distinct hostnames.")
if any(url.path not in ("", "/") or url.query or url.fragment or url.username is not None for url in urls):
    sys.exit("Site addresses must be origins without paths, credentials, queries or fragments.")
'
}

command=${1:-help}
[ "$#" -eq 0 ] || shift
case "$command" in
    up)
        validate_config
        compose up -d --build --wait --wait-timeout 600 "$@"
        ;;
    down)
        compose down --remove-orphans "$@"
        ;;
    restart)
        validate_config
        [ "$#" -gt 0 ] || { echo 'Usage: ./stack.sh restart SERVICE [...]' >&2; exit 1; }
        for service in "$@"; do
            case "$service" in
                frontend|support|reviewer|notifications|bot|scanner|caddy) ;;
                database|mattermost|bootstrap) echo 'Use ./stack.sh reset for chat/database/bootstrap changes.' >&2; exit 1 ;;
                *) echo "Unknown service: $service" >&2; exit 1 ;;
            esac
        done
        compose up -d --build --no-deps --force-recreate --wait --wait-timeout 600 "$@"
        ;;
    reset)
        validate_config
        [ "$#" -eq 0 ] || { echo 'Usage: ./stack.sh reset' >&2; exit 1; }
        compose down --remove-orphans
        compose up -d --build --wait --wait-timeout 600
        ;;
    logs)
        compose logs -f --tail=100 "$@"
        ;;
    monitor)
        monitor "$@"
        ;;
    *)
        echo 'Usage: ./stack.sh up | down | restart SERVICE [...] | reset | logs [SERVICE ...] | monitor [SECONDS]'
        [ "$command" = help ]
        ;;
esac
