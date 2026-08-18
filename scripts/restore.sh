#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE="${1:?usage: restore.sh backup.tgz}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
tar -C "$TMP" -xzf "$ARCHIVE"
cd "$ROOT"
if [[ -f "$TMP/.env" ]]; then
  cp "$TMP/.env" .env
fi
if [[ -d "$TMP/recordings" ]]; then
  mkdir -p data/recordings
  cp -a "$TMP/recordings/." data/recordings/
fi
docker compose up -d postgres
sleep 4
if [[ -f "$TMP/havenid.sql" ]]; then
  docker compose exec -T postgres psql -U haven -d havenid < "$TMP/havenid.sql"
fi
echo "Restore complete. Restart: docker compose up -d"
