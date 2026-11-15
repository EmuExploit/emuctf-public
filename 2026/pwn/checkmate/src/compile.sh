#!/bin/sh
set -eu
cd "$(dirname "$0")"
docker build --platform linux/amd64 -f compile.dockerfile -t checkmate-build .
docker run --rm --platform linux/amd64 -v "$PWD:/app" checkmate-build
