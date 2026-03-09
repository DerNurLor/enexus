#!/usr/bin/env bash
# =============================================================================
# deploy.sh — читает секреты из /run/secrets/* и запускает docker compose
# Использование:
#   sudo bash deploy.sh          # первый запуск / полный деплой
#   sudo bash deploy.sh pull     # git pull + rebuild + restart
#   sudo bash deploy.sh restart  # рестарт без пересборки
#   sudo bash deploy.sh logs     # логи
#   sudo bash deploy.sh status   # статус контейнеров
# =============================================================================
set -euo pipefail

SECRETS_DIR="/etc/ncfu/secrets"
COMPOSE_FILE="$(dirname "$(realpath "$0")")/docker-compose.yml"
COMPOSE_DIR="$(dirname "$COMPOSE_FILE")"

[[ $EUID -ne 0 ]] && {
  echo "❌ Запускай через: sudo bash deploy.sh"
  exit 1
}
[[ ! -d "$SECRETS_DIR" ]] && {
  echo "❌ Папка $SECRETS_DIR не найдена. Сначала: sudo bash setup-secrets.sh"
  exit 1
}

# ─── Читаем каждый файл из /run/secrets и экспортируем как переменную ─────────
_read() {
  local f="$SECRETS_DIR/$1"
  [[ -f "$f" ]] && cat "$f" || echo ""
}

export MONGO_USER="ncfu_app"
export MONGO_PASSWORD="$(_read mongo_password)"
export MONGO_DB="ncfu_schedule"
export AUTH_MONGO_DB="ncfu_auth"
export REDIS_PASSWORD="$(_read redis_password)"
export TELEGRAM_BOT_TOKEN="$(_read telegram_bot_token)"
export TELEGRAM_WEBHOOK_SECRET="$(_read telegram_webhook_secret)"
export OPENAI_API_KEY="$(_read openai_api_key)"
export JWT_SECRET="$(_read jwt_secret)"
export DASHBOARD_SECRET="$(_read dashboard_secret)"
export GRAPHQL_SECRET="$(_read graphql_secret)"
export MONGO_EXPRESS_PASSWORD="$(_read mongo_express_password)"
export SENTRY_DSN="$(_read sentry_dsn)"
export ADMIN_BOT_TOKEN="$(_read admin_bot_token)"
export SUPPORT_BOT_TOKEN="$(_read support_bot_token)"
export APP_ENV="production"
export ADMIN_PATH="admin"

# WEBHOOK_BASE_URL — спрашиваем если не задан
if [[ -f "$SECRETS_DIR/webhook_base_url" ]]; then
  export WEBHOOK_BASE_URL="$(_read webhook_base_url)"
elif [[ -z "${WEBHOOK_BASE_URL:-}" ]]; then
  read -rp "  Введи домен (https://yourdomain.com): " WEBHOOK_BASE_URL
  export WEBHOOK_BASE_URL
  echo "$WEBHOOK_BASE_URL" >"$SECRETS_DIR/webhook_base_url"
  chmod 600 "$SECRETS_DIR/webhook_base_url"
fi

export CORS_ALLOWED_ORIGINS="${WEBHOOK_BASE_URL}"

# ─── Проверка обязательных секретов ───────────────────────────────────────────
for var in MONGO_PASSWORD REDIS_PASSWORD TELEGRAM_BOT_TOKEN OPENAI_API_KEY JWT_SECRET; do
  [[ -z "${!var}" ]] && {
    echo "❌ Секрет $var пустой. Перезапусти setup-secrets.sh"
    exit 1
  }
done

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║            NCFU — Deploy                         ║"
echo "╚══════════════════════════════════════════════════╝"
echo "  Секреты:  $SECRETS_DIR ✅"
echo "  Домен:    $WEBHOOK_BASE_URL"
echo "  Команда:  ${1:-up}"
echo ""

cd "$COMPOSE_DIR"
CMD="${1:-up}"

case "$CMD" in
up | deploy | "")
  docker network create ncfu_network 2>/dev/null || true
  docker volume create ncfu_mongo_data 2>/dev/null || true
  docker compose -f "$COMPOSE_FILE" build --pull
  docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
  sleep 3
  docker compose -f "$COMPOSE_FILE" ps
  echo "✅ Деплой завершён"
  ;;
pull)
  git pull
  docker compose -f "$COMPOSE_FILE" build --pull
  docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
  echo "✅ Обновление завершено"
  ;;
restart)
  docker compose -f "$COMPOSE_FILE" restart
  docker compose -f "$COMPOSE_FILE" ps
  ;;
stop) docker compose -f "$COMPOSE_FILE" stop ;;
down) docker compose -f "$COMPOSE_FILE" down ;;
logs) docker compose -f "$COMPOSE_FILE" logs -f --tail=100 ;;
status) docker compose -f "$COMPOSE_FILE" ps ;;
*)
  echo "Команды: up, pull, restart, stop, down, logs, status"
  exit 1
  ;;
esac
