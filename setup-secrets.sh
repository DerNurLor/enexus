#!/usr/bin/env bash
# =============================================================================
# setup-secrets.sh — настройка секретов NCFU Bot Stack
# Хранит в /etc/ncfu/secrets (постоянно, переживёт ребут)
# Запускать: sudo bash setup-secrets.sh
# =============================================================================
set -euo pipefail

SECRETS_FILE="/etc/ncfu/secrets"

[[ $EUID -ne 0 ]] && { echo "❌ Запускай через: sudo bash setup-secrets.sh"; exit 1; }

mkdir -p /etc/ncfu
chmod 700 /etc/ncfu

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║       NCFU — Настройка секретов на сервере       ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

declare -A C
if [[ -f "$SECRETS_FILE" ]]; then
  echo "⚠️  Файл существует. Пустой ввод = оставить текущее."
  echo ""
  while IFS='=' read -r key val; do
    [[ "$key" =~ ^[[:space:]]*#.*$|^[[:space:]]*$ ]] && continue
    key="${key// /}"
    C["$key"]="${val}"
  done < "$SECRETS_FILE"
fi

ask() {
  local key="$1" prompt="$2" secret="${3:-false}"
  local cur="${C[$key]:-}"
  local display=""
  [[ -n "$cur" ]] && { [[ "$secret" == "true" ]] && display=" [${cur:0:4}****]" || display=" [$cur]"; }
  printf "  %s%s\n  > " "$prompt" "$display"
  local input; read -r input
  if [[ -n "$input" ]]; then
    C["$key"]="$input"
  elif [[ -z "$cur" ]]; then
    echo "  ⚠️  Обязательное поле!"; ask "$key" "$prompt" "$secret"
  fi
}

# ТОЛЬКО буквы и цифры — гарантированно совместим с MongoDB SASL, Redis, URL
safepass() {
  local key="$1" prompt="$2"
  if [[ -n "${C[$key]:-}" ]]; then
    printf "  %s [уже задан]\n" "$prompt"
  else
    C["$key"]="$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 32)"
    printf "  %s ✅ сгенерирован\n" "$prompt"
  fi
}

hexsecret() {
  local key="$1" prompt="$2" len="${3:-32}"
  if [[ -n "${C[$key]:-}" ]]; then
    printf "  %s [уже задан]\n" "$prompt"
  else
    C["$key"]="$(openssl rand -hex $len)"
    printf "  %s ✅ сгенерирован\n" "$prompt"
  fi
}

echo "── MongoDB ───────────────────────────────────────────"
C["MONGO_USER"]="${C[MONGO_USER]:-ncfu_app}"
C["MONGO_DB"]="${C[MONGO_DB]:-ncfu_schedule}"
C["AUTH_MONGO_DB"]="${C[AUTH_MONGO_DB]:-ncfu_auth}"
safepass MONGO_PASSWORD "Пароль MongoDB"
echo ""

echo "── Redis ─────────────────────────────────────────────"
safepass REDIS_PASSWORD "Пароль Redis"
echo ""

echo "── Telegram ──────────────────────────────────────────"
ask TELEGRAM_BOT_TOKEN "Токен бота (от @BotFather)" true
ask WEBHOOK_BASE_URL   "Домен (https://enexus.isabelline.xyz)" false
ask DOMAIN            "Домен без https (enexus.isabelline.xyz)" false
hexsecret TELEGRAM_WEBHOOK_SECRET "Webhook secret" 32
echo ""
echo "── Опциональные боты ─────────────────────────────"
ask SUPPORT_BOT_TOKEN "Support bot токен (необязательно, Enter=пропустить)" true
ask ADMIN_BOT_TOKEN   "Admin bot токен (необязательно, Enter=пропустить)" true
echo ""

echo "── OpenAI ────────────────────────────────────────────"
ask OPENAI_API_KEY "OpenAI API Key (sk-...)" true
echo ""

echo "── eCampus интеграция ────────────────────────────────"
echo "  TWOCAPTCHA_API_KEY — ключ 2captcha.com для авто-решения капчи."
echo "  Оставьте пустым если не используете авто-капчу (студенты вводят вручную)."
ask TWOCAPTCHA_API_KEY "2captcha API Key (необязательно)" true

echo ""
echo "  ECAMPUS_ENCRYPTION_KEY — 64 hex-символа (32 байта) для шифрования"
echo "  логинов и паролей eCampus в базе данных. ОБЯЗАТЕЛЬНО для безопасности."
if [[ -z "${C[ECAMPUS_ENCRYPTION_KEY]:-}" ]]; then
  C["ECAMPUS_ENCRYPTION_KEY"]="$(openssl rand -hex 32)"
  printf "  ECAMPUS_ENCRYPTION_KEY ✅ сгенерирован автоматически\n"
else
  printf "  ECAMPUS_ENCRYPTION_KEY [уже задан]\n"
fi
echo ""

echo "── Web-портал ────────────────────────────────────────"
echo "  WEB_URL — публичный URL веб-портала (используется в NEXT_PUBLIC_API_URL)."
echo "  Обычно совпадает с WEBHOOK_BASE_URL."
if [[ -z "${C[WEB_URL]:-}" ]]; then
  C["WEB_URL"]="${C[WEBHOOK_BASE_URL]:-}"
  [[ -n "${C[WEB_URL]}" ]] && printf "  WEB_URL ✅ скопирован из WEBHOOK_BASE_URL: %s\n" "${C[WEB_URL]}" \
                            || ask WEB_URL "Публичный URL веб-портала (https://...)" false
else
  printf "  WEB_URL [уже задан: %s]\n" "${C[WEB_URL]}"
fi
echo ""

echo "── Авто-генерация ────────────────────────────────────"
hexsecret JWT_SECRET       "JWT Secret"       32
hexsecret DASHBOARD_SECRET "Dashboard Secret" 16
hexsecret GRAPHQL_SECRET   "GraphQL Secret"   16
hexsecret BOT_API_SECRET   "Bot→API Secret"   16
echo ""

C["DOMAIN"]="${C[DOMAIN]:-${C[WEBHOOK_BASE_URL]:-localhost}}"
C["ADMIN_PATH"]="${C[ADMIN_PATH]:-admin}"
C["APP_ENV"]="${C[APP_ENV]:-production}"
C["BASE_URL"]="${C[BASE_URL]:-https://ecampus.ncfu.ru}"
C["SCRAPER_CONCURRENCY"]="${C[SCRAPER_CONCURRENCY]:-5}"
C["SCRAPE_INTERVAL_HOURS"]="${C[SCRAPE_INTERVAL_HOURS]:-1}"
C["CORS_ALLOWED_ORIGINS"]="${C[CORS_ALLOWED_ORIGINS]:-${C[WEBHOOK_BASE_URL]:-}}"
C["SUPPORT_BOT_TOKEN"]="${C[SUPPORT_BOT_TOKEN]:-}"
C["ADMIN_BOT_TOKEN"]="${C[ADMIN_BOT_TOKEN]:-}"
C["SUPPORT_ADMIN_CHAT_ID"]="${C[SUPPORT_ADMIN_CHAT_ID]:-0}"
C["SENTRY_DSN"]="${C[SENTRY_DSN]:-}"
C["TWOCAPTCHA_API_KEY"]="${C[TWOCAPTCHA_API_KEY]:-}"
C["WEB_URL"]="${C[WEB_URL]:-${C[WEBHOOK_BASE_URL]:-}}"
C["BOT_API_SECRET"]="${C[BOT_API_SECRET]:-}"

cat > "$SECRETS_FILE" << EOF
# /etc/ncfu/secrets — ТОЛЬКО ROOT — НЕ КОПИРОВАТЬ В GIT
# Обновлён: $(date -u '+%Y-%m-%d %H:%M UTC')

APP_ENV=${C[APP_ENV]}

MONGO_USER=${C[MONGO_USER]}
MONGO_PASSWORD=${C[MONGO_PASSWORD]}
MONGO_DB=${C[MONGO_DB]}
AUTH_MONGO_DB=${C[AUTH_MONGO_DB]}

REDIS_PASSWORD=${C[REDIS_PASSWORD]}

TELEGRAM_BOT_TOKEN=${C[TELEGRAM_BOT_TOKEN]}
TELEGRAM_WEBHOOK_SECRET=${C[TELEGRAM_WEBHOOK_SECRET]}
WEBHOOK_BASE_URL=${C[WEBHOOK_BASE_URL]}
DOMAIN=${C[DOMAIN]}
SUPPORT_BOT_TOKEN=${C[SUPPORT_BOT_TOKEN]}
ADMIN_BOT_TOKEN=${C[ADMIN_BOT_TOKEN]}
SUPPORT_ADMIN_CHAT_ID=${C[SUPPORT_ADMIN_CHAT_ID]}

OPENAI_API_KEY=${C[OPENAI_API_KEY]}

JWT_SECRET=${C[JWT_SECRET]}
DASHBOARD_SECRET=${C[DASHBOARD_SECRET]}
GRAPHQL_SECRET=${C[GRAPHQL_SECRET]}
BOT_API_SECRET=${C[BOT_API_SECRET]}

ADMIN_PATH=${C[ADMIN_PATH]}
CORS_ALLOWED_ORIGINS=${C[CORS_ALLOWED_ORIGINS]}

BASE_URL=${C[BASE_URL]}
SCRAPER_CONCURRENCY=${C[SCRAPER_CONCURRENCY]}
SCRAPE_INTERVAL_HOURS=${C[SCRAPE_INTERVAL_HOURS]}

# ── eCampus ──────────────────────────────────────────────
# ECAMPUS_ENCRYPTION_KEY: 64 hex-символа для AES-256-GCM шифрования credentials
ECAMPUS_ENCRYPTION_KEY=${C[ECAMPUS_ENCRYPTION_KEY]}
# TWOCAPTCHA_API_KEY: ключ для авто-решения капчи (пусто = только ручной ввод)
TWOCAPTCHA_API_KEY=${C[TWOCAPTCHA_API_KEY]}

# ── Web-портал ───────────────────────────────────────────
# WEB_URL: публичный URL для NEXT_PUBLIC_API_URL в Next.js
WEB_URL=${C[WEB_URL]}

SENTRY_DSN=${C[SENTRY_DSN]}
EOF

chmod 600 "$SECRETS_FILE"
chown root:root "$SECRETS_FILE"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅  Секреты сохранены в $SECRETS_FILE"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Следующий шаг: sudo bash deploy.sh"
echo ""
