# ═══════════════════════════════════════════════════════════════════════════════
# Makefile — управление стеком NCFU Schedule
#
# Все команды которые меняют состояние стека используют deploy.sh
# который загружает секреты из /etc/ncfu/secrets
#
# Примеры:
#   make up                    — поднять весь стек (с pre-deploy проверками)
#   make build miniapp         — пересобрать + перезапустить сервис
#   make pull                  — git pull + rebuild + restart
#   make check                 — только проверки без деплоя
#   make canary-up             — поднять canary (текущая ветка)
#   make canary-up BRANCH=feat — поднять canary из ветки feat/xxx
#   make canary 5              — направить 5% трафика на canary
#   make canary 0              — откатить canary (0% трафика)
#   make canary 100            — всё на canary
#   make canary-stable         — canary становится stable
#   make canary-status         — статус canary
#   make logs miniapp          — логи сервиса
#   make shell miniapp         — shell внутри контейнера
#   make mongo                 — MongoDB shell
#   make redis                 — Redis CLI
# ═══════════════════════════════════════════════════════════════════════════════

DEPLOY  = sudo bash deploy.sh
COMPOSE = docker compose

BOLD   = \033[1m
RESET  = \033[0m
GREEN  = \033[32m
CYAN   = \033[36m
RED    = \033[31m
YELLOW = \033[33m
DIM    = \033[2m

KNOWN_TARGETS := help up pull fresh stop down build restart logs status health \
                 check shell mongo redis canary canary-up canary-rollback \
                 canary-stable canary-status
EXTRA_ARGS    := $(filter-out $(firstword $(MAKECMDGOALS)), $(MAKECMDGOALS))
TARGETS       := $(or $(EXTRA_ARGS), $(svc))
BRANCH        ?=

.PHONY: help up pull fresh stop down build restart logs status health check \
        shell mongo redis canary canary-up canary-rollback canary-stable canary-status \
        backend bot miniapp dashboard nginx

# ── HELP ──────────────────────────────────────────────────────────────────────

help: ## Показать все команды
	@echo ""
	@echo "$(BOLD)NCFU — управление стеком$(RESET)"
	@echo ""
	@echo "$(CYAN)$(BOLD)ЗАПУСК$(RESET)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make up"                       "Поднять весь стек (с проверками + авто-откат)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make pull"                     "git pull + rebuild + restart"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make fresh"                    "Полный сброс (удаляет данные MongoDB!)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make stop"                     "Остановить стек"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make down"                     "Остановить и удалить контейнеры"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make restart"                  "Перезапустить без пересборки"
	@echo ""
	@echo "$(CYAN)$(BOLD)СБОРКА / ОБНОВЛЕНИЕ$(RESET)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make build miniapp"            "Пересобрать + перезапустить сервис"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make build backend bot"        "Пересобрать несколько сервисов"
	@echo ""
	@echo "$(CYAN)$(BOLD)ПРОВЕРКИ$(RESET)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make check"                    "Pre-deploy проверки (без деплоя)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make check backend"            "Проверить только backend"
	@echo ""
	@echo "$(CYAN)$(BOLD)CANARY ДЕПЛОЙ$(RESET)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make canary-up"                "Поднять canary (текущая ветка)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make canary-up BRANCH=feature" "Поднять canary из ветки"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make canary 5"                 "Направить 5%% трафика на canary"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make canary 50"                "Направить 50%% трафика на canary"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make canary 0"                 "Откатить (0%% = весь трафик на stable)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make canary-stable"            "Canary → stable (финальный promote)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make canary-rollback"          "Экстренный откат canary"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make canary-status"            "Статус canary"
	@echo ""
	@echo "$(CYAN)$(BOLD)МОНИТОРИНГ$(RESET)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make status"                   "Статус контейнеров"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make health"                   "Health-check всех сервисов"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make logs miniapp"             "Логи сервиса (tail -f)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make logs miniapp n=200"       "Последние N строк"
	@echo ""
	@echo "$(CYAN)$(BOLD)ДОСТУП$(RESET)"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make shell miniapp"            "Shell внутри контейнера"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make mongo"                    "MongoDB shell"
	@printf "  $(CYAN)%-40s$(RESET) %s\n" "make redis"                    "Redis CLI"
	@echo ""

# ── ЗАПУСК ────────────────────────────────────────────────────────────────────

up: ## Поднять весь стек
	$(DEPLOY) up

pull: ## git pull + rebuild + restart
	$(DEPLOY) pull

fresh: ## Полный сброс (удаляет MongoDB volume!)
	$(DEPLOY) fresh

stop: ## Остановить стек
	$(DEPLOY) stop

down: ## Остановить и удалить контейнеры
	$(DEPLOY) down

restart: ## Перезапустить без пересборки
	$(DEPLOY) restart

# ── СБОРКА ────────────────────────────────────────────────────────────────────

build: ## make build <сервис> [сервис2 ...] — пересобрать + перезапустить
ifneq ($(TARGETS),)
	$(DEPLOY) build "$(TARGETS)"
else
	@echo "$(RED)Укажи сервис: make build miniapp$(RESET)"
	@echo "$(DIM)Доступные: backend bot miniapp dashboard$(RESET)"
endif

# ── ПРОВЕРКИ ──────────────────────────────────────────────────────────────────

check: ## make check [сервис] — pre-deploy проверки
ifneq ($(TARGETS),)
	$(DEPLOY) check "$(TARGETS)"
else
	$(DEPLOY) check
endif

# ── CANARY ────────────────────────────────────────────────────────────────────

canary-up: ## Поднять canary backend (make canary-up BRANCH=feat/xxx)
	$(DEPLOY) canary-up "$(BRANCH)"

canary: ## make canary <процент> — направить N% трафика на canary (0 = откат)
ifneq ($(TARGETS),)
	@pct="$(TARGETS)"; \
	if [ "$$pct" = "0" ]; then \
		$(DEPLOY) canary-rollback; \
	else \
		$(DEPLOY) canary-promote "$$pct"; \
	fi
else
	@echo "$(RED)Укажи процент: make canary 5$(RESET)"
	@echo "$(DIM)0 = откатить весь трафик на stable$(RESET)"
endif

canary-rollback: ## Экстренный откат: весь трафик на stable
	$(DEPLOY) canary-rollback

canary-stable: ## Сделать canary новым stable
	$(DEPLOY) canary-stable

canary-status: ## Статус canary деплоя
	$(DEPLOY) canary-status

# ── МОНИТОРИНГ ────────────────────────────────────────────────────────────────

status: ## Статус контейнеров
	$(DEPLOY) status

health: ## Health-check всех сервисов
	@echo ""
	@echo "$(BOLD)Health checks:$(RESET)"
	@for svc_port in "backend:8000" "bot:8001" "miniapp:8002" "dashboard:8003"; do \
		svc=$$(echo $$svc_port | cut -d: -f1); \
		port=$$(echo $$svc_port | cut -d: -f2); \
		result=$$(curl -sf --max-time 5 http://localhost:$$port/health 2>/dev/null); \
		if [ $$? -eq 0 ]; then \
			echo "  $(GREEN)✓$(RESET) $(BOLD)$$svc$(RESET) $(DIM):$$port$(RESET) — $$result"; \
		else \
			echo "  $(RED)✗$(RESET) $(BOLD)$$svc$(RESET) $(DIM):$$port$(RESET) — $(RED)недоступен$(RESET)"; \
		fi; \
	done
	@# Canary health (если запущен)
	@if docker ps --filter "name=ncfu_backend_canary" --format "{{.Status}}" 2>/dev/null | grep -q "Up"; then \
		result=$$(curl -sf --max-time 5 http://localhost:8010/health 2>/dev/null); \
		if [ $$? -eq 0 ]; then \
			echo "  $(CYAN)✓$(RESET) $(BOLD)backend_canary$(RESET) $(DIM):8010$(RESET) — $$result"; \
		else \
			echo "  $(RED)✗$(RESET) $(BOLD)backend_canary$(RESET) $(DIM):8010$(RESET) — $(RED)недоступен$(RESET)"; \
		fi; \
	fi
	@echo ""

logs: ## make logs [сервис] [n=200]
ifneq ($(TARGETS),)
	$(COMPOSE) logs -f --tail=$(or $(n),100) $(TARGETS)
else
	$(COMPOSE) logs -f --tail=$(or $(n),100)
endif

# ── ДОСТУП ────────────────────────────────────────────────────────────────────

shell: ## make shell <сервис>
ifneq ($(TARGETS),)
	$(COMPOSE) exec $(TARGETS) /bin/sh
else
	@echo "$(RED)Укажи сервис: make shell miniapp$(RESET)"
endif

mongo: ## MongoDB shell
	@source /etc/ncfu/secrets && \
	$(COMPOSE) exec mongo mongosh \
		--username "$$MONGO_USER" \
		--password "$$MONGO_PASSWORD" \
		--authenticationDatabase admin

redis: ## Redis CLI
	@source /etc/ncfu/secrets && \
	$(COMPOSE) exec redis redis-cli -a "$$REDIS_PASSWORD"

# ── Заглушки для имён сервисов (чтобы make не ругался на неизвестные цели) ────
backend:  ;
bot:      ;
miniapp:  ;
dashboard: ;
nginx:    ;
