#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${1:-$ROOT/backups/havenid-$STAMP.tgz}"
mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if docker compose ps postgres --status running >/dev/null 2>&1; then
  docker compose exec -T postgres pg_dump -U haven havenid > "$TMP/havenid.sql"
fi
cp -a .env "$TMP/.env" 2>/dev/null || true
if [[ -d data/recordings ]]; then
  cp -a data/recordings "$TMP/recordings"
fi
tar -C "$TMP" -czf "$OUT" .
echo "Wrote $OUT"
