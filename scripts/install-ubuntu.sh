#!/usr/bin/env bash
# HavenID Ubuntu 22.04 / 24.04 installer. Run as a sudo-capable user.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $EUID -eq 0 ]]; then
  echo "Run as a normal user with sudo, not as root."
  exit 1
fi

sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg ufw

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
  echo "Docker installed. Log out and back in, then re-run this script."
  exit 0
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env. Edit BOOTSTRAP_EMAIL, passwords, HAVEN_DOMAIN, Twilio, then re-run."
  exit 0
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

if [[ -z "${HAVEN_DOMAIN:-}" || "${HAVEN_DOMAIN}" == "localhost" ]]; then
  echo "Set HAVEN_DOMAIN in .env to your DNS name before production."
fi

sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable || true

mkdir -p data/recordings backups
chmod 700 data/recordings

docker compose pull || true
docker compose up -d --build

echo "HavenID is starting. Point DNS A/AAAA for $HAVEN_DOMAIN at this host."
echo "Open https://$HAVEN_DOMAIN/login and sign in with BOOTSTRAP_EMAIL."
