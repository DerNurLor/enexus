#!/usr/bin/env bash
# =============================================================================
# deploy.sh — загружает /etc/ncfu/secrets и управляет стеком
#
# Использование:
#   sudo bash deploy.sh              # запустить / обновить (с проверками)
#   sudo bash deploy.sh build miniapp # пересобрать + перезапустить сервис
#   sudo bash deploy.sh restart      # рестарт без пересборки
#   sudo bash deploy.sh pull         # git pull + rebuild + restart
#   sudo bash deploy.sh stop         # остановить
#   sudo bash deploy.sh down         # остановить и удалить контейнеры
#   sudo bash deploy.sh logs [сервис] # логи
#   sudo bash deploy.sh status       # статус контейнеров
#   sudo bash deploy.sh fresh        # полный сброс (удаляет MongoDB volume!)
#   sudo bash deploy.sh check        # только проверки, без деплоя
#   sudo bash deploy.sh canary-up [ветка]        # поднять canary backend
#   sudo bash deploy.sh canary-promote <проц>    # направить N% трафика
#   sudo bash deploy.sh canary-rollback          # весь трафик на stable
#   sudo bash deploy.sh canary-stable            # сделать canary новым stable
#   sudo bash deploy.sh canary-status            # текущий статус canary
#   sudo bash deploy.sh staging-up               # поднять staging
#   sudo bash deploy.sh staging-down             # остановить staging
#   sudo bash deploy.sh staging-status           # статус staging
#   sudo bash deploy.sh staging-health           # health-check staging
#   sudo bash deploy.sh staging-logs [сервис]    # логи staging
#   sudo bash deploy.sh staging-build <сервис>   # пересобрать сервис в staging
#   sudo bash deploy.sh staging-set-webhook      # зарегистрировать webhook бота
# =============================================================================
set -euo pipefail

SECRETS_FILE="/etc/ncfu/secrets"
STAGING_SECRETS_FILE="/etc/ncfu/secrets.staging"
DIR="$(dirname "$(realpath "$0")")"
CANARY_STATE_FILE="/etc/ncfu/canary.state"
STAGING_COMPOSE_FILE="$DIR/docker-compose.staging.yml"
STAGING_PROJECT="ncfu_staging"
BOLD='\033[1m'; GREEN='\033[32m'; RED='\033[31m'; YELLOW='\033[33m'; CYAN='\033[36m'; RESET='\033[0m'

[[ $EUID -ne 0 ]] && { echo -e "${RED}❌ Запускай через: sudo bash deploy.sh${RESET}"; exit 1; }

# ── Загрузка секретов ─────────────────────────────────────────────────────────
if [[ ! -f "$SECRETS_FILE" ]]; then
  echo -e "${RED}❌ Нет $SECRETS_FILE${RESET}"
  echo "   Запусти сначала: sudo bash setup-secrets.sh"
  exit 1
fi
set -a; source "$SECRETS_FILE"; set +a

REQUIRED=(MONGO_PASSWORD REDIS_PASSWORD TELEGRAM_BOT_TOKEN OPENAI_API_KEY JWT_SECRET)
for v in "${REQUIRED[@]}"; do
  [[ -z "${!v:-}" ]] && { echo -e "${RED}❌ Пустой секрет: $v${RESET}"; echo "   sudo bash setup-secrets.sh"; exit 1; }
done
for v in MONGO_PASSWORD REDIS_PASSWORD; do
  [[ "${!v}" =~ [^a-zA-Z0-9] ]] && { echo -e "${RED}❌ $v содержит спецсимволы!${RESET}"; exit 1; }
done

cd "$DIR"

# ═══════════════════════════════════════════════════════════════════════════════
# PRE-DEPLOY ПРОВЕРКИ
# ═══════════════════════════════════════════════════════════════════════════════
_run_checks() {
  local target="${1:-all}"
  local errors=0

  echo -e "\n${BOLD}╔══════════════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}║         Pre-deploy проверки                  ║${RESET}"
  echo -e "${BOLD}╚══════════════════════════════════════════════╝${RESET}"

  # 1. docker-compose конфиг валиден
  echo -ne "  ${CYAN}[1/4]${RESET} docker-compose.yml синтаксис ... "
  if docker compose config --quiet 2>/dev/null; then
    echo -e "${GREEN}✓${RESET}"
  else
    echo -e "${RED}✗${RESET}"
    docker compose config 2>&1 | head -20
    ((errors++))
  fi

  # 2. Python синтаксис — ищем ошибки в .py файлах без запуска контейнеров
  echo -ne "  ${CYAN}[2/4]${RESET} Python синтаксис ... "
  local py_errors=0
  local dirs_to_check=()
  case "$target" in
    backend)   dirs_to_check=(backend) ;;
    bot)       dirs_to_check=(ecampus_bot) ;;
    miniapp)   dirs_to_check=(miniapp) ;;
    *)         dirs_to_check=(backend ecampus_bot miniapp) ;;
  esac
  for svc_dir in "${dirs_to_check[@]}"; do
    [[ ! -d "$DIR/$svc_dir/app" ]] && continue
    while IFS= read -r -d '' pyfile; do
      if ! python3 -m py_compile "$pyfile" 2>/tmp/_ncfu_py_err; then
        [[ $py_errors -eq 0 ]] && echo ""
        echo -e "    ${RED}✗${RESET} ${pyfile#$DIR/}"
        cat /tmp/_ncfu_py_err | sed 's/^/      /'
        ((py_errors++))
      fi
    done < <(find "$DIR/$svc_dir/app" -name "*.py" -print0 2>/dev/null)
  done
  rm -f /tmp/_ncfu_py_err
  if [[ $py_errors -eq 0 ]]; then echo -e "${GREEN}✓${RESET}"; else ((errors++)); fi

  # 3. Все обязательные секреты заданы (уже проверили выше, дублируем для читаемости)
  echo -ne "  ${CYAN}[3/4]${RESET} Обязательные секреты ... "
  local sec_errors=0
  for v in OPENAI_API_KEY JWT_SECRET DASHBOARD_SECRET; do
    [[ -z "${!v:-}" ]] && { echo -e "\n    ${RED}✗${RESET} $v пустой"; ((sec_errors++)); }
  done
  [[ $sec_errors -eq 0 ]] && echo -e "${GREEN}✓${RESET}" || ((errors++))

  # 4. requirements.txt существуют и не пустые
  echo -ne "  ${CYAN}[4/4]${RESET} requirements.txt ... "
  local req_errors=0
  for svc_dir in backend ecampus_bot miniapp; do
    req="$DIR/$svc_dir/requirements.txt"
    if [[ ! -f "$req" ]] || [[ ! -s "$req" ]]; then
      echo -e "\n    ${RED}✗${RESET} не найден: $req"
      ((req_errors++))
    fi
  done
  [[ $req_errors -eq 0 ]] && echo -e "${GREEN}✓${RESET}" || { ((errors++)); }

  echo ""
  if [[ $errors -gt 0 ]]; then
    echo -e "${RED}${BOLD}❌ Найдено $errors ошибок. Деплой отменён.${RESET}\n"
    return 1
  fi
  echo -e "${GREEN}${BOLD}✅ Все проверки пройдены.${RESET}\n"
  return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# POST-DEPLOY HEALTH VERIFICATION + АВТОМАТИЧЕСКИЙ ОТКАТ
# ═══════════════════════════════════════════════════════════════════════════════
declare -A _SVC_PORT=([backend]=8000 [bot]=8001 [miniapp]=8002 [dashboard]=8003)

_verify_health() {
  local timeout="${1:-90}"
  local step=5
  local elapsed=0

  echo -e "${BOLD}Ожидание health-check (до ${timeout}s)...${RESET}"

  while [[ $elapsed -lt $timeout ]]; do
    local all_ok=1
    for svc in backend bot miniapp; do
      port="${_SVC_PORT[$svc]}"
      curl -sf --max-time 3 "http://127.0.0.1:${port}/health" &>/dev/null || { all_ok=0; break; }
    done

    if [[ $all_ok -eq 1 ]]; then
      echo ""
      for svc in backend bot miniapp; do
        port="${_SVC_PORT[$svc]}"
        resp=$(curl -sf --max-time 3 "http://127.0.0.1:${port}/health" 2>/dev/null || echo "{}")
        echo -e "  ${GREEN}✓${RESET} ${BOLD}${svc}${RESET}:${port}  $resp"
      done
      echo -e "\n${GREEN}${BOLD}✅ Все сервисы здоровы.${RESET}"
      return 0
    fi

    printf "  проверка... %ds/%ds\r" "$elapsed" "$timeout"
    sleep $step; ((elapsed += step))
  done

  echo -e "\n${RED}${BOLD}❌ Health-check провалился после ${timeout}s${RESET}"
  for svc in backend bot miniapp; do
    port="${_SVC_PORT[$svc]}"
    if ! curl -sf --max-time 3 "http://127.0.0.1:${port}/health" &>/dev/null; then
      echo -e "  ${RED}✗${RESET} ${svc}:${port} — недоступен"
      echo -e "  ${YELLOW}Последние логи ${svc}:${RESET}"
      docker compose logs --tail=25 "$svc" 2>/dev/null | sed 's/^/    /' || true
    fi
  done
  return 1
}

_save_previous() {
  for svc in backend bot miniapp; do
    local img="ncfu_${svc}:latest"
    docker image inspect "$img" &>/dev/null && docker tag "$img" "ncfu_${svc}:previous" 2>/dev/null || true
  done
  echo -e "  ${CYAN}Текущие образы сохранены как :previous${RESET}"
}

_rollback() {
  echo -e "\n${YELLOW}${BOLD}⚠️  Откатываемся на предыдущие образы (:previous)...${RESET}"
  local rolled=0
  for svc in backend bot miniapp; do
    local prev="ncfu_${svc}:previous"
    if docker image inspect "$prev" &>/dev/null 2>&1; then
      echo -e "  откат ${svc} → ${prev}"
      docker compose stop "$svc" 2>/dev/null || true
      docker tag "$prev" "ncfu_${svc}:latest"
      docker compose up -d --no-deps --no-build "$svc" 2>/dev/null || true
      ((rolled++))
    fi
  done
  if [[ $rolled -gt 0 ]]; then
    echo -e "${YELLOW}Откат выполнен ($rolled сервисов). Проверь: sudo bash deploy.sh status${RESET}"
  else
    echo -e "${RED}Нет сохранённых :previous образов для отката${RESET}"
  fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# CANARY УПРАВЛЕНИЕ
# ═══════════════════════════════════════════════════════════════════════════════
_canary_up() {
  local branch="${1:-}"
  echo -e "${CYAN}${BOLD}▶ Поднимаем canary backend...${RESET}"

  if [[ -n "$branch" ]]; then
    echo -e "  Ветка: ${BOLD}$branch${RESET}"
    git -C "$DIR" stash 2>/dev/null || true
    git -C "$DIR" checkout "$branch" 2>/dev/null || { echo -e "${RED}❌ Ветка $branch не найдена${RESET}"; exit 1; }
  fi

  echo "  Сборка ncfu_backend:canary ..."
  docker build \
    --file "$DIR/backend/Dockerfile" \
    --target runtime \
    --tag "ncfu_backend:canary" \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    "$DIR" 2>&1 | grep -E "(Step|DONE|error|ERROR)" | tail -10

  if [[ -n "$branch" ]]; then
    git -C "$DIR" checkout - 2>/dev/null || true
    git -C "$DIR" stash pop 2>/dev/null || true
  fi

  if [[ ! -f "$DIR/docker-compose.canary.yml" ]]; then
    echo -e "${RED}❌ Нет docker-compose.canary.yml — создай его сначала${RESET}"
    exit 1
  fi
  docker compose -f "$DIR/docker-compose.yml" -f "$DIR/docker-compose.canary.yml" \
    up -d --no-deps backend_canary 2>&1

  mkdir -p /etc/ncfu
  echo "CANARY_BRANCH=${branch:-current}" > "$CANARY_STATE_FILE"
  echo "CANARY_PERCENT=0" >> "$CANARY_STATE_FILE"
  echo "CANARY_STARTED=$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$CANARY_STATE_FILE"

  sleep 5
  if curl -sf --max-time 5 "http://127.0.0.1:8010/health" &>/dev/null; then
    resp=$(curl -sf --max-time 5 "http://127.0.0.1:8010/health")
    echo -e "${GREEN}✅ Canary backend здоров: $resp${RESET}"
    echo "   Направь трафик: sudo bash deploy.sh canary-promote 5"
  else
    echo -e "${RED}❌ Canary backend не отвечает на :8010/health${RESET}"
    echo "   Логи: docker logs ncfu_backend_canary"
    exit 1
  fi
}

_canary_promote() {
  local pct="${1:-}"
  if [[ -z "$pct" ]] || ! [[ "$pct" =~ ^[0-9]+$ ]] || [[ $pct -gt 100 ]]; then
    echo -e "${RED}❌ Укажи процент 0-100: sudo bash deploy.sh canary-promote 10${RESET}"; exit 1
  fi

  if ! curl -sf --max-time 5 "http://127.0.0.1:8010/health" &>/dev/null; then
    echo -e "${RED}❌ Canary backend не отвечает! Сначала подними: sudo bash deploy.sh canary-up${RESET}"; exit 1
  fi

  echo -e "${CYAN}${BOLD}▶ Направляем ${pct}% трафика на canary...${RESET}"

  export CANARY_PERCENT="$pct"
  export NGINX_ADMIN_PATH="${ADMIN_PATH:-admin}"
  export NGINX_DOMAIN="${DOMAIN:-localhost}"

  envsubst '$NGINX_ADMIN_PATH $NGINX_DOMAIN $CANARY_PERCENT' \
    < "$DIR/nginx/nginx.canary.conf.template" \
    | sed 's/\$\$/$/g' \
    > /tmp/_ncfu_nginx_canary.conf

  docker cp /tmp/_ncfu_nginx_canary.conf ncfu_nginx:/etc/nginx/nginx.conf
  rm -f /tmp/_ncfu_nginx_canary.conf

  if docker exec ncfu_nginx nginx -t 2>/dev/null; then
    docker exec ncfu_nginx nginx -s reload
    sed -i "s/CANARY_PERCENT=.*/CANARY_PERCENT=$pct/" "$CANARY_STATE_FILE" 2>/dev/null || \
      echo "CANARY_PERCENT=$pct" >> "$CANARY_STATE_FILE"
    echo -e "${GREEN}✅ ${pct}% трафика → canary${RESET}"
    [[ $pct -eq 100 ]] && echo -e "${YELLOW}  Если всё ок — сделай stable: sudo bash deploy.sh canary-stable${RESET}"
  else
    echo -e "${RED}❌ Ошибка nginx конфига${RESET}"; docker exec ncfu_nginx nginx -t; exit 1
  fi
}

_canary_rollback() {
  echo -e "${YELLOW}${BOLD}▶ Откат canary → весь трафик на stable...${RESET}"
  export NGINX_ADMIN_PATH="${ADMIN_PATH:-admin}"
  export NGINX_DOMAIN="${DOMAIN:-localhost}"

  envsubst '$NGINX_ADMIN_PATH $NGINX_DOMAIN' \
    < "$DIR/nginx/nginx.conf.template" \
    | sed 's/\$\$/$/g' \
    > /tmp/_ncfu_nginx_stable.conf

  docker cp /tmp/_ncfu_nginx_stable.conf ncfu_nginx:/etc/nginx/nginx.conf
  rm -f /tmp/_ncfu_nginx_stable.conf
  docker exec ncfu_nginx nginx -s reload

  sed -i "s/CANARY_PERCENT=.*/CANARY_PERCENT=0/" "$CANARY_STATE_FILE" 2>/dev/null || true
  docker compose stop backend_canary 2>/dev/null || true
  echo -e "${GREEN}✅ Весь трафик на stable. Canary остановлен.${RESET}"
}

_canary_stable() {
  echo -e "${CYAN}${BOLD}▶ Canary → stable...${RESET}"
  _save_previous
  docker tag ncfu_backend:canary ncfu_backend:latest
  docker compose up -d --no-deps --no-build backend
  sleep 5
  if curl -sf --max-time 5 "http://127.0.0.1:8000/health" &>/dev/null; then
    _canary_rollback
    echo -e "${GREEN}✅ Canary стал новым stable. Деплой завершён.${RESET}"
  else
    echo -e "${RED}❌ Stable backend не отвечает после promote! Откатываемся...${RESET}"
    _rollback
    exit 1
  fi
}

_canary_status() {
  echo -e "\n${BOLD}Статус canary:${RESET}"
  if docker ps --filter "name=ncfu_backend_canary" --format "{{.Status}}" 2>/dev/null | grep -q "Up"; then
    echo -e "  Контейнер: ${GREEN}запущен${RESET}"
    if curl -sf --max-time 3 "http://127.0.0.1:8010/health" &>/dev/null; then
      resp=$(curl -sf --max-time 3 "http://127.0.0.1:8010/health")
      echo -e "  Health:    ${GREEN}OK${RESET}  $resp"
    else
      echo -e "  Health:    ${RED}не отвечает${RESET}"
    fi
  else
    echo -e "  Контейнер: ${YELLOW}не запущен${RESET}"
  fi
  if [[ -f "$CANARY_STATE_FILE" ]]; then
    echo "  ---"
    cat "$CANARY_STATE_FILE" | sed 's/^/  /'
  fi
  echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# STAGING
# ═══════════════════════════════════════════════════════════════════════════════
_staging_compose() {
  if [[ ! -f "$STAGING_SECRETS_FILE" ]]; then
    echo -e "${RED}❌ Нет $STAGING_SECRETS_FILE${RESET}"
    echo "   Создай: sudo cp /etc/ncfu/secrets /etc/ncfu/secrets.staging"
    echo "   И замени: TELEGRAM_BOT_TOKEN, WEBHOOK_BASE_URL, DOMAIN"
    exit 1
  fi
  set -a; source "$STAGING_SECRETS_FILE"; set +a
  docker compose \
    --env-file "$STAGING_SECRETS_FILE" \
    -p "$STAGING_PROJECT" \
    -f "$STAGING_COMPOSE_FILE" \
    "$@"
}

_staging_up() {
  echo -e "${CYAN}${BOLD}▶ Поднимаем staging...${RESET}"
  # docker network create ncfu_staging_network 2>/dev/null || true
  docker volume  create ncfu_staging_mongo_data 2>/dev/null || true
  _staging_compose build --pull
  _staging_compose up -d --remove-orphans
  echo -e "${GREEN}${BOLD}✅ Staging поднят.${RESET}"
  echo -e "   Логи:    make staging-logs backend"
  echo -e "   Health:  make staging-health"
  echo -e "   Стоп:    make staging-down"
}

_staging_down() {
  echo -e "${YELLOW}▶ Останавливаем staging...${RESET}"
  docker compose -p "$STAGING_PROJECT" down
  echo -e "${GREEN}✅ Staging остановлен.${RESET}"
}

_staging_status() {
  echo -e "\n${BOLD}Статус staging:${RESET}"
  docker compose -p "$STAGING_PROJECT" ps 2>/dev/null || echo "  не запущен"
  echo ""
}

_staging_health() {
  echo -e "\n${BOLD}Health checks (staging):${RESET}"
  declare -A _STAGING_PORT=([backend]=18000 [bot]=18001 [miniapp]=18002 [dashboard]=18003)
  for svc in backend bot miniapp; do
    port="${_STAGING_PORT[$svc]}"
    if curl -sf --max-time 5 "http://127.0.0.1:${port}/health" &>/dev/null; then
      resp=$(curl -sf --max-time 5 "http://127.0.0.1:${port}/health" 2>/dev/null)
      echo -e "  ${GREEN}✓${RESET} ${BOLD}${svc}${RESET}:${port}  $resp"
    else
      echo -e "  ${RED}✗${RESET} ${BOLD}${svc}${RESET}:${port} — недоступен"
    fi
  done
  echo ""
}

_staging_set_webhook() {
  if [[ ! -f "$STAGING_SECRETS_FILE" ]]; then
    echo -e "${RED}❌ Нет $STAGING_SECRETS_FILE${RESET}"; exit 1
  fi
  # Перезагружаем секреты из staging-файла
  set -a; source "$STAGING_SECRETS_FILE"; set +a
  echo -e "${CYAN}▶ Регистрируем webhook staging бота...${RESET}"
  resp=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
    --data-urlencode "url=${WEBHOOK_BASE_URL}/webhook/telegram" \
    -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}")
  echo "  $resp"
  echo -e "${GREEN}✅ Webhook: ${WEBHOOK_BASE_URL}/webhook/telegram${RESET}"
}

# ═══════════════════════════════════════════════════════════════════════════════
_ensure_infra() {
  docker network create ncfu_network    2>/dev/null || true
  docker volume  create ncfu_mongo_data 2>/dev/null || true
}

CMD="${1:-up}"; SVCS="${2:-}"

case "$CMD" in
  up|"")
    echo -e "${BOLD}▶ Деплой стека...${RESET}"
    _run_checks "all" || exit 1
    _save_previous
    _ensure_infra
    docker compose build --pull
    docker compose up -d --remove-orphans
    if ! _verify_health 90; then
      echo -e "\n${RED}${BOLD}⚠️  Деплой провалился. Автооткат...${RESET}"
      _rollback; exit 1
    fi
    docker compose ps
    echo -e "${GREEN}${BOLD}✅ Стек запущен и здоров.${RESET}"
    ;;

  build)
    [[ -z "$SVCS" ]] && { echo -e "${RED}❌ Укажи сервис: sudo bash deploy.sh build miniapp${RESET}"; exit 1; }
    echo -e "${BOLD}▶ Пересборка + перезапуск: $SVCS${RESET}"
    _run_checks "$SVCS" || exit 1
    _save_previous
    docker compose build $SVCS
    docker compose up -d --no-deps $SVCS
    sleep 8
    for svc in $SVCS; do
      port="${_SVC_PORT[$svc]:-}"
      [[ -z "$port" ]] && continue
      if curl -sf --max-time 5 "http://127.0.0.1:${port}/health" &>/dev/null; then
        resp=$(curl -sf --max-time 5 "http://127.0.0.1:${port}/health" 2>/dev/null)
        echo -e "  ${GREEN}✓${RESET} $svc:$port  $resp"
      else
        echo -e "  ${RED}✗${RESET} $svc:$port не отвечает — откатываемся"
        _rollback; exit 1
      fi
    done
    echo -e "${GREEN}✅ Готово: $SVCS${RESET}"
    ;;

  check)
    _run_checks "${SVCS:-all}"
    ;;

  restart)
    echo -e "${BOLD}▶ Рестарт...${RESET}"
    _ensure_infra
    docker compose up -d --remove-orphans
    docker compose ps
    ;;

  pull)
    echo -e "${BOLD}▶ Git pull + rebuild...${RESET}"
    _run_checks "all" || exit 1
    git -C "$DIR" pull
    _save_previous
    _ensure_infra
    docker compose build --pull
    docker compose up -d --remove-orphans
    if ! _verify_health 90; then
      echo -e "${RED}${BOLD}⚠️  Деплой провалился. Автооткат...${RESET}"
      _rollback; exit 1
    fi
    echo -e "${GREEN}${BOLD}✅ Обновление завершено.${RESET}"
    ;;

  fresh)
    echo -e "${YELLOW}${BOLD}⚠️  ВНИМАНИЕ: удаляем MongoDB volume — все данные будут потеряны!${RESET}"
    read -rp "  Продолжить? (yes/no): " confirm
    [[ "$confirm" != "yes" ]] && { echo "Отменено."; exit 0; }
    docker compose down
    docker volume rm ncfu_mongo_data 2>/dev/null || true
    docker volume create ncfu_mongo_data
    docker compose build --pull
    docker compose up -d --remove-orphans
    echo -e "${GREEN}✅ Стек пересоздан с нуля${RESET}"
    ;;

  stop)   docker compose stop ;;
  down)   docker compose down ;;

  logs)
    [[ -n "$SVCS" ]] && docker compose logs -f --tail=100 $SVCS \
                      || docker compose logs -f --tail=100
    ;;

  status) docker compose ps ;;

  canary-up)       _canary_up "${SVCS:-}" ;;
  canary-promote)  _canary_promote "${SVCS:-}" ;;
  canary-rollback) _canary_rollback ;;
  canary-stable)   _canary_stable ;;
  canary-status)   _canary_status ;;

  staging-up)          _staging_up ;;
  staging-down)        _staging_down ;;
  staging-status)      _staging_status ;;
  staging-health)      _staging_health ;;
  staging-set-webhook) _staging_set_webhook ;;
  staging-logs)
    _staging_compose logs -f --tail="${3:-100}" ${SVCS:-}
    ;;
  staging-build)
    [[ -z "$SVCS" ]] && { echo -e "${RED}❌ Укажи сервис: sudo bash deploy.sh staging-build miniapp${RESET}"; exit 1; }
    _staging_compose build --no-cache $SVCS
    _staging_compose up -d --no-deps $SVCS
    echo -e "${GREEN}✅ Staging $SVCS пересобран.${RESET}"
    ;;
  
  staging-rebuild)
    [[ -z "$SVCS" ]] && { echo -e "${RED}❌ Укажи сервис: make staging-rebuild web${RESET}"; exit 1; }
    docker stop ncfu_staging_${SVCS} 2>/dev/null || true
    docker rm ncfu_staging_${SVCS} 2>/dev/null || true
    docker rmi ncfu_${SVCS}:staging 2>/dev/null || true
    _staging_compose build --no-cache $SVCS
    _staging_compose up -d --no-deps $SVCS
    echo -e "${GREEN}✅ Staging $SVCS пересобран без кеша.${RESET}"
    ;;

  *)
    echo -e "${BOLD}Команды:${RESET}"
    echo "  Основные:   up | build <сервис> | restart | pull | fresh | stop | down"
    echo "  Проверки:   check [сервис]"
    echo "  Мониторинг: logs [сервис] | status"
    echo "  Canary:     canary-up [ветка] | canary-promote <N%>"
    echo "              canary-rollback | canary-stable | canary-status"
    echo "  Staging:    staging-up | staging-down | staging-status | staging-health"
    echo "              staging-logs [сервис] | staging-build <сервис> | staging-set-webhook"
    exit 1
    ;;
esac
