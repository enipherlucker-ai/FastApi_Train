#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

TAG="${1:?передай тег образа: ./deploy.sh <тег>}"

sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=${TAG}/" .env
grep -q "^IMAGE_TAG=${TAG}$" .env

docker compose pull
docker compose up -d --remove-orphans

for i in $(seq 1 30); do
  if docker compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/openapi.json', timeout=2)" 2>/dev/null; then
    echo "API отвечает, версия ${TAG}"
    docker compose ps
    docker image prune -af --filter "until=168h"
    exit 0
  fi
  sleep 2
done

echo "API не ответило за 60 секунд" >&2
docker compose logs --tail=50 api >&2
exit 1