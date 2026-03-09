#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# setup-secrets.sh — интерактивная настройка секретов на сервере
# Запускать с sudo:  sudo bash setup-secrets.sh
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; exit 1; }
ask()   { local v; read -rsp "    $1: " v; echo; printf '%s' "$v"; }

[[ $EUID -ne 0 ]] && error "Запусти с sudo: sudo bash $0"

DIR="/run/secrets"
mkdir -p "$DIR" && chmod 700 "$DIR"

w() { printf '%s' "$2" > "$DIR/$1"; chmod 600 "$DIR/$1"; info "Записан: $DIR/$1"; }

echo -e "\n══════════════════════════════════════════════"
echo   "  Настройка секретов NCFU Bot Stack"
echo -e "══════════════════════════════════════════════\n"

echo "▸ MongoDB"
P=$(ask "Пароль MongoDB"); [[ -z "$P" ]] && error "Не может быть пустым"; w mongo_password "$P"

echo -e "\n▸ Redis"
P=$(ask "Пароль Redis"); [[ -z "$P" ]] && error "Не может быть пустым"; w redis_password "$P"

echo -e "\n▸ Telegram"
P=$(ask "Токен основного бота (от @BotFather)"); [[ -z "$P" ]] && error "Не может быть пустым"
w telegram_bot_token "$P"
w telegram_webhook_secret "$(openssl rand -hex 32 | tr -d '\n')"
info "  Webhook secret сгенерирован автоматически"

warn "Дополнительные боты (Enter = пропустить):"
P=$(ask "Токен бота поддержки"); [[ -n "$P" ]] && w support_bot_token "$P"
P=$(ask "Токен admin-бота");     [[ -n "$P" ]] && w admin_bot_token "$P"

echo -e "\n▸ OpenAI"
P=$(ask "OpenAI API Key (sk-...)"); [[ -z "$P" ]] && error "Не может быть пустым"; w openai_api_key "$P"

echo -e "\n▸ JWT & Dashboard (генерируются автоматически)"
w jwt_secret             "$(openssl rand -hex 64 | tr -d '\n')"
w dashboard_secret       "$(openssl rand -hex 32 | tr -d '\n')"
w graphql_secret         "$(openssl rand -hex 32 | tr -d '\n')"
w mongo_express_password "$(openssl rand -hex 16 | tr -d '\n')"

echo ""
P=$(ask "Sentry DSN (Enter = пропустить)"); [[ -n "$P" ]] && w sentry_dsn "$P"

echo -e "\n══════════════════════════════════════════════"
info "Готово! Все секреты записаны в $DIR"
echo -e "\nФайлы:"; ls -la "$DIR"
echo ""
warn "Следующий шаг:"
echo "  docker network create ncfu_network"
echo "  docker volume create ncfu_mongo_data"
echo "  docker compose -f docker-compose.prod.yml up -d --build"
echo "══════════════════════════════════════════════"
