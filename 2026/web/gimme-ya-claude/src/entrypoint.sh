#!/bin/sh
set -eu

: "${flag:=EMU{local_test_flag}}"
printf '%s' "$flag" > /secret/flag.txt
chown root:root /secret/flag.txt
chmod 400 /secret/flag.txt
chmod 711 /secret
unset flag

mkdir -p /tmp/home
cat > /tmp/home/.claude.json <<'JSON'
{
  "hasCompletedOnboarding": true,
  "bypassPermissionsModeAccepted": false,
  "theme": "dark"
}
JSON
chown -R app:app /tmp/home

chown app:app /app/tmp /app/log 2>/dev/null || true

export SECRET_KEY_BASE="b7f1c0d9a84e3526f0a1c7d4e9b28f635a1d4c8e70f29b6d53a8c1e04f7b2d9608c3e5a2b1f7d4069e8c2a5f3b0d16e7a4c9f2b8d5e1a07c3f6b94d2e8a1c5073"

cd /app
exec gosu app bundle exec puma -C config/puma.rb
