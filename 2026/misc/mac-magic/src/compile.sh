#!/bin/sh
set -eu
cd "$(dirname "$0")"
docker build --platform linux/amd64 -t mac-magic-local .
