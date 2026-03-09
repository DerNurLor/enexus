# ═══════════════════════════════════════════════════════════════════════════════
# Makefile — управление стеком NCFU Schedule
#
# Сервисы приложения:  backend  bot  miniapp  dashboard
# Инфраструктура:      mongo  redis  nginx
#
# Примеры:
#   make help                          — все команды с описанием
#   make up                            — поднять весь стек
#   make dev                           — dev-режим (hot-reload + открытые порты)
#
#   make build backend dashboard       — собрать конкретные сервисы (через пробел)
#   make build                         — интерактивный checkbox-выбор
#   make build-all                     — пересобрать ВСЕ (--no-cache)
#
#   make rebuild backend dashboard     — собрать + перезапустить несколько сервисов
#   make rebuild bot                   — собрать + перезапустить один сервис
#   make rebuild                       — интерактивный выбор
#
#   make deploy backend                — rolling deploy одного сервиса
#   make restart miniapp               — перезапустить без пересборки
#   make restart                       — перезапустить всё
#
#   make logs backend                  — логи конкретного сервиса
#   make logs backend n=200            — последние N строк
#   make shell backend                 — shell в контейнере
# ═══════════════════════════════════════════════════════════════════════════════

# ── Переменные ────────────────────────────────────────────────────────────────

COMPOSE     = docker compose
COMPOSE_DEV = docker compose -f docker-compose.yml -f docker-compose.dev.yml

# Все сервисы приложения (не инфра)
APP_SERVICES = backend bot miniapp dashboard

# Цвета для вывода
BOLD  = \033[1m
RESET = \033[0m
GREEN = \033[32m
CYAN  = \033[36m
RED   = \033[31m
YELLOW= \033[33m
DIM   = \033[2m

# Загружаем .env если есть (для mongo/redis shell команд)
-include .env
export

# ── Перехват позиционных аргументов ──────────────────────────────────────────
#
# Позволяет писать:  make build backend dashboard bot
# Вместо:           make build svc="backend dashboard bot"
#
# Как работает:
#   1. KNOWN_TARGETS — все цели Makefile; остальные аргументы считаем сервисами
#   2. MAKECMDGOALS содержит всё что передано в команде (цель + доп. слова)
#   3. Фильтруем: из MAKECMDGOALS убираем первый аргумент (цель) → EXTRA_ARGS
#   4. Цели-заглушки в конце файла поглощают имена сервисов без ошибки

KNOWN_TARGETS := help up dev down stop build build-all rebuild deploy \
                 restart restart-all ps status health logs logs-all \
                 shell shell-mongo shell-redis pull pull-app \
                 gen-secrets env-check clean clean-images clean-volumes \
                 _health-one

# Слова из командной строки, которые НЕ являются основной целью
EXTRA_ARGS := $(filter-out $(firstword $(MAKECMDGOALS)), $(MAKECMDGOALS))

# Итоговый список сервисов: позиционные аргументы ИЛИ svc= ИЛИ пусто (→ интерактив)
TARGETS := $(or $(EXTRA_ARGS), $(svc))

# ── Утилиты ───────────────────────────────────────────────────────────────────

# Красивый заголовок действия
define print_action
	@echo ""
	@echo "$(BOLD)$(CYAN)▶ $(1)$(RESET)"
	@echo "$(DIM)────────────────────────────────────────$(RESET)"
endef

.PHONY: help \
        up dev down stop \
        build build-all \
        rebuild deploy \
        restart restart-all \
        pull pull-app \
        ps status health \
        logs logs-all \
        shell shell-mongo shell-redis \
        gen-secrets env-check \
        clean clean-images clean-volumes

# ── HELP ──────────────────────────────────────────────────────────────────────

help: ## Показать все команды
	@echo ""
	@echo "$(BOLD)NCFU Schedule — управление стеком$(RESET)"
	@echo ""
	@echo "$(CYAN)$(BOLD)ЗАПУСК$(RESET)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make up"                       "Поднять весь стек (production)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make dev"                      "Dev-режим (hot-reload + открытые порты)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make down"                     "Остановить всё и удалить контейнеры"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make stop"                     "Остановить без удаления контейнеров"
	@echo ""
	@echo "$(CYAN)$(BOLD)СБОРКА$(RESET)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make build backend dashboard"  "Собрать один или несколько сервисов"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make build"                    "Интерактивный checkbox-выбор (↑↓ Пробел Enter)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make build-all"                "Пересобрать ВСЕ образы (--no-cache)"
	@echo ""
	@echo "$(CYAN)$(BOLD)ПЕРЕСБОРКА + ПЕРЕЗАПУСК$(RESET)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make rebuild backend bot"      "Собрать + перезапустить несколько сервисов"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make rebuild dashboard"        "Собрать + перезапустить один сервис"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make rebuild"                  "Интерактивный выбор + перезапуск"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make deploy backend"           "Rolling deploy (build + up --no-deps)"
	@echo ""
	@echo "$(CYAN)$(BOLD)ПЕРЕЗАПУСК$(RESET)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make restart miniapp"          "Перезапустить один сервис"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make restart backend bot"      "Перезапустить несколько сервисов"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make restart"                  "Перезапустить все сервисы"
	@echo ""
	@echo "$(CYAN)$(BOLD)ЛОГИ$(RESET)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make logs"                     "Логи всех сервисов (tail -f)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make logs backend"             "Логи конкретного сервиса"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make logs backend n=200"       "Последние N строк"
	@echo ""
	@echo "$(CYAN)$(BOLD)МОНИТОРИНГ$(RESET)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make ps"                       "Статус всех контейнеров"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make status"                   "Подробный статус + CPU/RAM"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make health"                   "Health-check всех сервисов"
	@echo ""
	@echo "$(CYAN)$(BOLD)ДОСТУП$(RESET)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make shell backend"            "Shell внутри контейнера"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make shell-mongo"              "MongoDB shell (mongosh)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make shell-redis"              "Redis CLI"
	@echo ""
	@echo "$(CYAN)$(BOLD)ОБНОВЛЕНИЕ$(RESET)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make pull"                     "Обновить базовые образы + пересобрать приложения"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make pull-app"                 "Обновить только инфра (mongo/redis/nginx)"
	@echo ""
	@echo "$(CYAN)$(BOLD)УТИЛИТЫ$(RESET)"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make gen-secrets"              "Сгенерировать секреты для .env"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make env-check"                "Проверить .env на обязательные поля"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make clean"                    "Удалить остановленные контейнеры"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make clean-images"             "Удалить неиспользуемые образы"
	@printf "  $(CYAN)%-36s$(RESET) %s\n" "make clean-volumes"            "$(RED)ВНИМАНИЕ: удалить все данные$(RESET)"
	@echo ""

# ── ЗАПУСК / ОСТАНОВКА ────────────────────────────────────────────────────────

up: env-check ## Поднять весь стек (production)
	$(call print_action,Запуск стека...)
	$(COMPOSE) up -d
	@echo ""
	@echo "$(GREEN)✓ Стек запущен$(RESET)"
	@$(MAKE) --no-print-directory ps

dev: env-check ## Поднять в dev-режиме (hot-reload + открытые порты + mongo-express)
	$(call print_action,Запуск в dev-режиме...)
	$(COMPOSE_DEV) --profile dev up -d
	@echo ""
	@echo "$(GREEN)✓ Dev-стек запущен$(RESET)"
	@echo "$(DIM)  backend:       http://localhost:8000/docs$(RESET)"
	@echo "$(DIM)  bot:           http://localhost:8001/health$(RESET)"
	@echo "$(DIM)  miniapp:       http://localhost:8002/docs$(RESET)"
	@echo "$(DIM)  dashboard:     http://localhost:8003/dashboard/admin$(RESET)"
	@echo "$(DIM)  mongo-express: http://localhost:8081$(RESET)"
	@echo "$(DIM)  nginx:         http://localhost:80$(RESET)"

down: ## Остановить всё и удалить контейнеры
	$(call print_action,Остановка стека...)
	$(COMPOSE) --profile dev down
	@echo "$(GREEN)✓ Стек остановлен$(RESET)"

stop: ## Остановить без удаления контейнеров
	$(call print_action,Пауза стека (контейнеры сохранены)...)
	$(COMPOSE) --profile dev stop

# ── СБОРКА ────────────────────────────────────────────────────────────────────

BUILD_SCRIPT = ./scripts/select-build.sh

# build: позиционные аргументы / svc= / интерактивный выбор
# Примеры:
#   make build backend dashboard   ← через пробел
#   make build svc=backend         ← старый синтаксис, тоже работает
#   make build                     ← интерактивный checkbox
build: ## make build [сервис1 сервис2 ...] — или без аргументов для интерактива
ifneq ($(TARGETS),)
	$(call print_action,Сборка: $(TARGETS))
	$(COMPOSE) build $(TARGETS)
	@echo "$(GREEN)✓ Собрано: $(TARGETS)$(RESET)"
	@echo "$(DIM)Запусти 'make restart $(TARGETS)' чтобы применить$(RESET)"
else
	@SVCS=$$(bash $(BUILD_SCRIPT) build) && \
	if [ -n "$$SVCS" ]; then \
		echo "" && \
		echo "$(BOLD)$(CYAN)▶ Сборка: $$SVCS$(RESET)" && \
		echo "$(DIM)────────────────────────────────────────$(RESET)" && \
		$(COMPOSE) build $$SVCS && \
		echo "" && \
		echo "$(GREEN)✓ Собрано: $$SVCS$(RESET)" && \
		echo "$(DIM)Запусти 'make restart' чтобы применить$(RESET)"; \
	fi
endif

build-all: ## Пересобрать ВСЕ образы с --no-cache
	$(call print_action,Полная пересборка всех образов (без кеша)...)
	@echo "$(YELLOW)⚠ Это займёт несколько минут...$(RESET)"
	$(COMPOSE) build --no-cache $(APP_SERVICES)
	@echo "$(GREEN)✓ Все образы пересобраны$(RESET)"

# ── REBUILD (build + перезапуск) ──────────────────────────────────────────────

rebuild: ## make rebuild [сервис1 сервис2 ...] — или без аргументов для интерактива
ifneq ($(TARGETS),)
	$(call print_action,Rebuild + restart: $(TARGETS))
	$(COMPOSE) build $(TARGETS)
	$(COMPOSE) up -d --no-deps $(TARGETS)
	@echo "$(GREEN)✓ Пересобрано и перезапущено: $(TARGETS)$(RESET)"
	@sleep 3
	@for s in $(TARGETS); do $(MAKE) --no-print-directory _health-one SVC=$$s; done
else
	@SVCS=$$(bash $(BUILD_SCRIPT) rebuild) && \
	if [ -n "$$SVCS" ]; then \
		echo "" && \
		echo "$(BOLD)$(CYAN)▶ Rebuild: $$SVCS$(RESET)" && \
		echo "$(DIM)────────────────────────────────────────$(RESET)" && \
		$(COMPOSE) build $$SVCS && \
		$(COMPOSE) up -d --no-deps $$SVCS && \
		echo "" && \
		echo "$(GREEN)✓ Пересобрано и перезапущено: $$SVCS$(RESET)" && \
		sleep 3 && \
		for s in $$SVCS; do $(MAKE) --no-print-directory _health-one SVC=$$s; done; \
	fi
endif

# ── DEPLOY (rolling: build + up --no-deps) ───────────────────────────────────

deploy: ## make deploy [сервис1 сервис2 ...] — или без аргументов для интерактива
ifneq ($(TARGETS),)
	$(call print_action,Rolling deploy: $(TARGETS))
	$(COMPOSE) build $(TARGETS)
	$(COMPOSE) up -d --no-deps $(TARGETS)
	@echo "$(GREEN)✓ Задеплоено: $(TARGETS)$(RESET)"
	@sleep 3
	@for s in $(TARGETS); do $(MAKE) --no-print-directory _health-one SVC=$$s; done
else
	@SVCS=$$(bash $(BUILD_SCRIPT) deploy) && \
	if [ -n "$$SVCS" ]; then \
		echo "" && \
		echo "$(BOLD)$(CYAN)▶ Deploy: $$SVCS$(RESET)" && \
		echo "$(DIM)────────────────────────────────────────$(RESET)" && \
		$(COMPOSE) build $$SVCS && \
		$(COMPOSE) up -d --no-deps $$SVCS && \
		echo "" && \
		echo "$(GREEN)✓ Задеплоено: $$SVCS$(RESET)" && \
		sleep 3 && \
		for s in $$SVCS; do $(MAKE) --no-print-directory _health-one SVC=$$s; done; \
	fi
endif

# ── RESTART ───────────────────────────────────────────────────────────────────

restart: ## make restart [сервис1 сервис2 ...] — или без аргументов → всё
ifneq ($(TARGETS),)
	$(call print_action,Перезапуск: $(TARGETS))
	$(COMPOSE) restart $(TARGETS)
	@echo "$(GREEN)✓ Перезапущено: $(TARGETS)$(RESET)"
	@sleep 2
	@for s in $(TARGETS); do $(MAKE) --no-print-directory _health-one SVC=$$s; done
else
	$(call print_action,Перезапуск всех сервисов...)
	$(COMPOSE) restart
	@echo "$(GREEN)✓ Все сервисы перезапущены$(RESET)"
endif

restart-all: ## Перезапустить все сервисы
	$(call print_action,Перезапуск всех сервисов...)
	$(COMPOSE) restart
	@echo "$(GREEN)✓ Готово$(RESET)"

# ── СТАТУС / МОНИТОРИНГ ───────────────────────────────────────────────────────

ps: ## Краткий статус контейнеров
	@$(COMPOSE) --profile dev ps

status: ## Подробный статус + использование CPU/RAM
	@echo ""
	@echo "$(BOLD)Контейнеры:$(RESET)"
	@$(COMPOSE) --profile dev ps
	@echo ""
	@echo "$(BOLD)Ресурсы:$(RESET)"
	@docker stats --no-stream \
		ncfu_backend ncfu_bot ncfu_miniapp ncfu_dashboard \
		ncfu_mongo ncfu_redis ncfu_nginx 2>/dev/null || true

health: ## Проверить health-endpoint всех сервисов
	@echo ""
	@echo "$(BOLD)Health checks:$(RESET)"
	@echo ""
	@$(MAKE) --no-print-directory _health-one SVC=backend  PORT=8000
	@$(MAKE) --no-print-directory _health-one SVC=bot      PORT=8001
	@$(MAKE) --no-print-directory _health-one SVC=miniapp  PORT=8002
	@$(MAKE) --no-print-directory _health-one SVC=dashboard PORT=8003
	@echo ""

# Внутренняя цель — проверить health одного сервиса
_health-one:
	@SVC=$(or $(SVC),$(svc)); \
	PORT=$(PORT); \
	if [ -z "$$PORT" ]; then \
		case "$$SVC" in \
			backend)   PORT=8000 ;; \
			bot)       PORT=8001 ;; \
			miniapp)   PORT=8002 ;; \
			dashboard) PORT=8003 ;; \
			*)         echo "$(DIM)  $$SVC — health не проверяется$(RESET)"; exit 0 ;; \
		esac; \
	fi; \
	RESULT=$$(curl -sf --max-time 5 http://localhost:$$PORT/health 2>/dev/null); \
	if [ $$? -eq 0 ]; then \
		STATUS=$$(echo "$$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null || echo "ok"); \
		echo "  $(GREEN)✓$(RESET) $(BOLD)$$SVC$(RESET) $(DIM):$$PORT$(RESET) — $$STATUS"; \
	else \
		echo "  $(RED)✗$(RESET) $(BOLD)$$SVC$(RESET) $(DIM):$$PORT$(RESET) — $(RED)недоступен$(RESET)"; \
	fi

# ── ЛОГИ ──────────────────────────────────────────────────────────────────────

# n= задаёт количество строк (по умолчанию 100)
LOG_LINES ?= 100

logs: ## make logs [сервис] [n=200] — один сервис или все
ifneq ($(TARGETS),)
	$(COMPOSE) logs -f --tail=$(or $(n),$(LOG_LINES)) $(TARGETS)
else
	$(COMPOSE) logs -f --tail=$(or $(n),$(LOG_LINES))
endif

logs-all: ## Все логи без фильтра (без -f)
	$(COMPOSE) --profile dev logs --tail=50

# ── ДОСТУП / SHELL ────────────────────────────────────────────────────────────

shell: ## make shell <сервис> — shell внутри контейнера
	@if [ -z "$(TARGETS)" ]; then \
		echo "$(RED)Ошибка: укажи сервис: make shell backend$(RESET)"; \
		echo "$(DIM)Доступные: $(APP_SERVICES) mongo redis nginx$(RESET)"; \
		exit 1; \
	fi
	$(COMPOSE) exec $(TARGETS) /bin/sh

shell-mongo: ## MongoDB shell (mongosh)
	$(call print_action,MongoDB shell...)
	$(COMPOSE) exec mongo mongosh \
		--username "$(MONGO_USER)" \
		--password "$(MONGO_PASSWORD)" \
		--authenticationDatabase admin

shell-redis: ## Redis CLI
	$(call print_action,Redis CLI...)
	$(COMPOSE) exec redis redis-cli -a "$(REDIS_PASSWORD)"

# ── ОБНОВЛЕНИЕ ОБРАЗОВ ────────────────────────────────────────────────────────

pull: ## Обновить все базовые образы (mongo, redis, nginx, python)
	$(call print_action,Обновление базовых образов...)
	$(COMPOSE) pull mongo redis nginx
	@echo "$(DIM)Пересборка приложений после обновления базовых образов:$(RESET)"
	$(COMPOSE) build $(APP_SERVICES)
	@echo "$(GREEN)✓ Все образы обновлены. Запусти 'make up' для применения$(RESET)"

pull-app: ## Обновить только инфра-образы (mongo/redis/nginx) без пересборки
	$(COMPOSE) pull mongo redis nginx
	@echo "$(GREEN)✓ Инфра-образы обновлены$(RESET)"

# ── УТИЛИТЫ ───────────────────────────────────────────────────────────────────

gen-secrets: ## Сгенерировать все секреты и вывести в консоль
	@echo ""
	@echo "$(BOLD)Скопируй в .env:$(RESET)"
	@echo "$(DIM)─────────────────────────────────────────────────$(RESET)"
	@echo "JWT_SECRET=$$(openssl rand -hex 64)"
	@echo "DASHBOARD_SECRET=$$(openssl rand -hex 32)"
	@echo "GRAPHQL_SECRET=$$(openssl rand -hex 32)"
	@echo "TELEGRAM_WEBHOOK_SECRET=$$(openssl rand -hex 32)"
	@echo "MONGO_PASSWORD=$$(openssl rand -base64 32 | tr -d '=+/' | head -c 40)"
	@echo "REDIS_PASSWORD=$$(openssl rand -base64 32 | tr -d '=+/' | head -c 40)"
	@echo "MONGO_EXPRESS_PASSWORD=$$(openssl rand -base64 16 | tr -d '=+/')"
	@echo "$(DIM)─────────────────────────────────────────────────$(RESET)"
	@echo ""

env-check: ## Проверить .env на наличие обязательных полей
	@if [ ! -f .env ]; then \
		echo "$(RED)✗ Файл .env не найден!$(RESET)"; \
		echo "$(DIM)  Создай: cp .env.example .env$(RESET)"; \
		exit 1; \
	fi
	@MISSING=""; \
	for var in MONGO_USER MONGO_PASSWORD REDIS_PASSWORD JWT_SECRET \
	           TELEGRAM_BOT_TOKEN OPENAI_API_KEY DASHBOARD_SECRET; do \
		val=$$(grep -E "^$$var=" .env | cut -d= -f2- | tr -d '"' | tr -d "'"); \
		if [ -z "$$val" ] || echo "$$val" | grep -qiE "CHANGE_ME|your_|sk-\.\.\.|^0$$"; then \
			MISSING="$$MISSING $$var"; \
		fi; \
	done; \
	if [ -n "$$MISSING" ]; then \
		echo "$(YELLOW)⚠ Не заполнены поля в .env:$(RESET)"; \
		for v in $$MISSING; do echo "  $(RED)✗$(RESET) $$v"; done; \
		echo ""; \
	else \
		echo "$(GREEN)✓ .env заполнен$(RESET)"; \
	fi

clean: ## Удалить остановленные контейнеры и dangling образы
	$(call print_action,Очистка...)
	docker container prune -f
	docker image prune -f
	@echo "$(GREEN)✓ Очищено$(RESET)"

clean-images: ## Удалить все неиспользуемые образы
	$(call print_action,Удаление неиспользуемых образов...)
	docker image prune -af
	@echo "$(GREEN)✓ Образы удалены$(RESET)"

clean-volumes: ## ⚠ УДАЛИТЬ ВСЕ ДАННЫЕ (mongo volumes)
	@echo "$(RED)$(BOLD)⚠ ВНИМАНИЕ: это удалит ВСЕ данные MongoDB!$(RESET)"
	@printf "$(BOLD)Введи 'yes' для подтверждения: $(RESET)" && read confirm && \
	if [ "$$confirm" = "yes" ]; then \
		$(COMPOSE) --profile dev down -v; \
		echo "$(GREEN)✓ Volumes удалены$(RESET)"; \
	else \
		echo "$(DIM)Отмена$(RESET)"; \
	fi

# ── Поглощение имён сервисов как позиционных аргументов ───────────────────────
# make воспринимает всё в командной строке как цели.
# Эти заглушки объявляют имена сервисов (и часто используемые флаги) как
# фиктивные пустые цели — иначе make ругается "No rule to make target 'backend'".
#
# Механизм:
#   make build backend dashboard
#   → MAKECMDGOALS = "build backend dashboard"
#   → EXTRA_ARGS   = "backend dashboard"         (отфильтровали "build")
#   → TARGETS      = "backend dashboard"
#   → цель build   получает TARGETS и запускает: docker compose build backend dashboard
#   → цели backend и dashboard — пустые заглушки, ошибки нет

.PHONY: backend bot miniapp dashboard mongo redis nginx

backend:  ;
bot:      ;
miniapp:  ;
dashboard: ;
mongo:    ;
redis:    ;
nginx:    ;
