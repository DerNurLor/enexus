#!/usr/bin/env bash
# =============================================================================
# deploy.sh — деплой / обновление стека на сервере
#
# Использование:
#   sudo bash deploy.sh             # полный деплой (pull + build + up)
#   sudo bash deploy.sh restart     # только рестарт без пересборки
#   sudo bash deploy.sh logs        # tail логов всех сервисов
#   sudo bash deploy.sh status      # статус контейнеров
#   sudo bash deploy.sh pull        # git pull + rebuild без даунтайма
# =============================================================================

set -euo pipefail

SECRETS_FILE="/etc/ncfu/secrets"
COMPOSE_FILE="$(dirname "$(realpath "$0")")/docker-compose.yml"
COMPOSE_DIR="$(dirname "$COMPOSE_FILE")"

# ─── Проверки ──────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
  echo "❌  Запускай через: sudo bash deploy.sh"
  exit 1
fi

if [[ ! -f "$SECRETS_FILE" ]]; then
  echo "❌  Файл секретов не найден: $SECRETS_FILE"
  echo "   Сначала запусти: sudo bash setup-secrets.sh"
  exit 1
fi

# Проверяем права — должен быть 600
PERMS="$(stat -c '%a' "$SECRETS_FILE")"
if [[ "$PERMS" != "600" ]]; then
  echo "⚠️  Права на $SECRETS_FILE: $PERMS (ожидалось 600)"
  echo "   Исправляю..."
  chmod 600 "$SECRETS_FILE"
fi

# ─── Загружаем секреты в окружение текущего процесса ──────────────────────────
# set -a экспортирует все переменные автоматически
set -a
# shellcheck disable=SC1090
source "$SECRETS_FILE"
set +a

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║            NCFU — Deploy Script                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Секреты:   $SECRETS_FILE ✅"
echo "  Compose:   $COMPOSE_FILE"
echo "  Команда:   ${1:-up}"
echo ""

cd "$COMPOSE_DIR"

CMD="${1:-up}"

case "$CMD" in

  up|deploy|"")
    echo "▶ Инициализация Docker volumes и сетей..."
    docker network  create ncfu_network  2>/dev/null || true
    docker volume   create ncfu_mongo_data 2>/dev/null || true

    echo "▶ Сборка образов..."
    docker compose -f "$COMPOSE_FILE" build --pull

    echo "▶ Запуск сервисов..."
    docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

    echo ""
    echo "▶ Ожидание health checks..."
    sleep 5
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
    echo "✅  Деплой завершён"
    ;;

  pull)
    echo "▶ git pull..."
    git pull

    echo "▶ Пересборка образов без остановки сервисов..."
    docker compose -f "$COMPOSE_FILE" build --pull

    echo "▶ Rolling restart..."
    docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

    echo "✅  Обновление завершено"
    ;;

  restart)
    echo "▶ Перезапуск..."
    docker compose -f "$COMPOSE_FILE" restart
    docker compose -f "$COMPOSE_FILE" ps
    ;;

  stop)
    echo "▶ Остановка..."
    docker compose -f "$COMPOSE_FILE" stop
    ;;

  down)
    echo "▶ Остановка и удаление контейнеров..."
    docker compose -f "$COMPOSE_FILE" down
    ;;

  logs)
    docker compose -f "$COMPOSE_FILE" logs -f --tail=100
    ;;

  status|ps)
    docker compose -f "$COMPOSE_FILE" ps
    ;;

  *)
    echo "Неизвестная команда: $CMD"
    echo "Доступные: up, pull, restart, stop, down, logs, status"
    exit 1
    ;;

esac
