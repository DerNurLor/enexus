#!/usr/bin/env bash
# =============================================================================
# deploy.sh — загружает /etc/ncfu/secrets и управляет стеком
#
# Использование:
#   sudo bash deploy.sh              # запустить / обновить
#   sudo bash deploy.sh build miniapp # пересобрать + перезапустить сервис
#   sudo bash deploy.sh restart      # рестарт без пересборки
#   sudo bash deploy.sh pull         # git pull + rebuild + restart
#   sudo bash deploy.sh stop         # остановить
#   sudo bash deploy.sh down         # остановить и удалить контейнеры
#   sudo bash deploy.sh logs [сервис] # логи
#   sudo bash deploy.sh status       # статус контейнеров
#   sudo bash deploy.sh fresh        # полный сброс (удаляет MongoDB volume!)
# =============================================================================
set -euo pipefail

SECRETS_FILE="/etc/ncfu/secrets"
DIR="$(dirname "$(realpath "$0")")"

[[ $EUID -ne 0 ]] && { echo "❌ Запускай через: sudo bash deploy.sh"; exit 1; }

if [[ ! -f "$SECRETS_FILE" ]]; then
  echo "❌ Нет $SECRETS_FILE"
  echo "   Запусти сначала: sudo bash setup-secrets.sh"
  exit 1
fi

# Загружаем секреты
set -a
source "$SECRETS_FILE"
set +a

# Проверяем обязательные переменные
REQUIRED=(MONGO_PASSWORD REDIS_PASSWORD TELEGRAM_BOT_TOKEN OPENAI_API_KEY JWT_SECRET)
for v in "${REQUIRED[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "❌ Пустой секрет: $v"
    echo "   Запусти: sudo bash setup-secrets.sh"
    exit 1
  fi
done

# Проверяем что пароли не содержат спецсимволов
for v in MONGO_PASSWORD REDIS_PASSWORD; do
  val="${!v}"
  if [[ "$val" =~ [^a-zA-Z0-9] ]]; then
    echo "❌ $v содержит спецсимволы — сломает MongoDB/Redis!"
    echo "   Запусти setup-secrets.sh и затем: sudo bash deploy.sh fresh"
    exit 1
  fi
done

cd "$DIR"

_ensure_infra() {
  docker network create ncfu_network    2>/dev/null || true
  docker volume  create ncfu_mongo_data 2>/dev/null || true
}

CMD="${1:-up}"
SVCS="${2:-}"

case "$CMD" in
  up|"")
    echo "▶ Запуск стека..."
    _ensure_infra
    docker compose build --pull
    docker compose up -d --remove-orphans
    sleep 3
    docker compose ps
    echo "✅ Стек запущен"
    ;;

  build)
    if [[ -z "$SVCS" ]]; then
      echo "❌ Укажи сервис: sudo bash deploy.sh build miniapp"
      exit 1
    fi
    echo "▶ Пересборка + перезапуск: $SVCS"
    docker compose build $SVCS
    docker compose up -d --no-deps $SVCS
    sleep 3
    docker compose ps $SVCS
    echo "✅ Готово: $SVCS"
    ;;

  restart)
    echo "▶ Рестарт..."
    _ensure_infra
    docker compose up -d --remove-orphans
    docker compose ps
    ;;

  pull)
    echo "▶ Git pull + rebuild..."
    git -C "$DIR" pull
    _ensure_infra
    docker compose build --pull
    docker compose up -d --remove-orphans
    echo "✅ Обновление завершено"
    ;;

  fresh)
    echo "⚠️  ВНИМАНИЕ: удаляем MongoDB volume — все данные будут потеряны!"
    read -rp "  Продолжить? (yes/no): " confirm
    [[ "$confirm" != "yes" ]] && { echo "Отменено."; exit 0; }
    docker compose down
    docker volume rm ncfu_mongo_data 2>/dev/null || true
    docker volume create ncfu_mongo_data
    docker compose build --pull
    docker compose up -d --remove-orphans
    echo "✅ Стек пересоздан с нуля"
    ;;

  stop)   docker compose stop ;;
  down)   docker compose down ;;

  logs)
    if [[ -n "$SVCS" ]]; then
      docker compose logs -f --tail=100 $SVCS
    else
      docker compose logs -f --tail=100
    fi
    ;;

  status) docker compose ps ;;

  *)
    echo "Команды: up, build <сервис>, restart, pull, fresh, stop, down, logs [сервис], status"
    exit 1
    ;;
esac
