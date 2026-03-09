# ═══════════════════════════════════════════════════════════════════════════════
# Makefile — управление стеком NCFU Schedule
#
# Все команды которые меняют состояние стека используют deploy.sh
# который загружает секреты из /etc/ncfu/secrets
#
# Примеры:
#   make up                    — поднять весь стек
#   make build miniapp         — пересобрать + перезапустить сервис
#   make pull                  — git pull + rebuild + restart
#   make fresh                 — полный сброс (удаляет данные!)
#   make logs miniapp          — логи сервиса
#   make shell miniapp         — shell внутри контейнера
#   make mongo                 — MongoDB shell
#   make redis                 — Redis CLI
# ═══════════════════════════════════════════════════════════════════════════════

DEPLOY = sudo bash deploy.sh
COMPOSE = docker compose

BOLD   = \033[1m
RESET  = \033[0m
GREEN  = \033[32m
CYAN   = \033[36m
RED    = \033[31m
DIM    = \033[2m

# Поглощаем имена сервисов как позиционные аргументы
KNOWN_TARGETS := help up pull fresh stop down build restart logs status health shell mongo redis
EXTRA_ARGS    := $(filter-out $(firstword $(MAKECMDGOALS)), $(MAKECMDGOALS))
TARGETS       := $(or $(EXTRA_ARGS), $(svc))

.PHONY: help up pull fresh stop down build restart logs status health shell mongo redis \
        backend bot miniapp dashboard nginx

# ── HELP ──────────────────────────────────────────────────────────────────────

help: ## Показать все команды
	@echo ""
	@echo "$(BOLD)NCFU — управление стеком$(RESET)"
	@echo ""
	@echo "$(CYAN)$(BOLD)ЗАПУСК$(RESET)"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make up"                    "Поднять весь стек"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make pull"                  "git pull + rebuild + restart"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make fresh"                 "Полный сброс (удаляет данные MongoDB!)"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make stop"                  "Остановить стек"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make down"                  "Остановить и удалить контейнеры"
	@echo ""
	@echo "$(CYAN)$(BOLD)СБОРКА / ОБНОВЛЕНИЕ$(RESET)"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make build miniapp"         "Пересобрать + перезапустить сервис"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make build backend bot"     "Пересобрать несколько сервисов"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make restart"               "Перезапустить без пересборки"
	@echo ""
	@echo "$(CYAN)$(BOLD)МОНИТОРИНГ$(RESET)"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make status"                "Статус контейнеров"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make health"                "Health-check всех сервисов"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make logs miniapp"          "Логи сервиса (tail -f)"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make logs miniapp n=200"    "Последние N строк"
	@echo ""
	@echo "$(CYAN)$(BOLD)ДОСТУП$(RESET)"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make shell miniapp"         "Shell внутри контейнера"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make mongo"                 "MongoDB shell"
	@printf "  $(CYAN)%-35s$(RESET) %s\n" "make redis"                 "Redis CLI"
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
			echo "  $(GREEN)✓$(RESET) $(BOLD)$$svc$(RESET) $(DIM):$$port$(RESET) — ok"; \
		else \
			echo "  $(RED)✗$(RESET) $(BOLD)$$svc$(RESET) $(DIM):$$port$(RESET) — $(RED)недоступен$(RESET)"; \
		fi; \
	done
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

# ── Заглушки для имён сервисов ────────────────────────────────────────────────
backend:  ;
bot:      ;
miniapp:  ;
dashboard: ;
nginx:    ;
