# NCFU Schedule Bot — Документация

Полная система расписания СКФУ: Telegram-бот с AI, Mini App, REST/GraphQL API и админ-панель.

---

## Содержание

- [Архитектура](#архитектура)
- [Стек технологий](#стек-технологий)
- [Первый деплой (с нуля)](#первый-деплой-с-нуля)
- [Получение секретных ключей](#получение-секретных-ключей)
- [Переменные окружения](#переменные-окружения)
- [Управление стеком — Makefile](#управление-стеком--makefile)
- [deploy.sh — детали](#deploysh--детали)
- [API Reference](#api-reference)
- [Структура репозитория](#структура-репозитория)
- [Обновление и CI](#обновление-и-ci)
- [Автозапуск через systemd](#автозапуск-через-systemd)
- [Troubleshooting](#troubleshooting)

---

## Архитектура

```
                         Internet
                            │
                     ┌──────▼──────┐
                     │    Nginx    │  :80 → единая точка входа
                     └──────┬──────┘
          ┌──────────────────┼────────────────────┐
          │                  │                    │
    ┌─────▼─────┐     ┌──────▼──────┐     ┌──────▼──────┐
    │  backend  │     │     bot     │     │   miniapp   │
    │   :8000   │     │    :8001    │     │    :8002    │
    │ REST/GQL  │◄────│  Telegram   │     │  SPA + API  │
    │  Scraper  │     │  aiogram 3  │     │  Mini App   │
    └─────┬─────┘     └─────────────┘     └─────────────┘
          │
    ┌─────▼──────┐
    │  dashboard │
    │    :8003   │
    │ Админ-панель│
    └─────┬──────┘
          │
    ┌─────▼───────────────────────┐
    │  MongoDB :27017 │ Redis :6379│
    └─────────────────────────────┘
```

### Сервисы

| Сервис | Порт | Назначение |
|---|---|---|
| `backend` | 8000 | REST API расписания, GraphQL, веб-скрапер, планировщик |
| `bot` | 8001 | Telegram-бот (webhook, AI-обработка, команды) |
| `miniapp` | 8002 | Telegram Mini App: SPA (React) + FastAPI |
| `dashboard` | 8003 | Админ-панель: пользователи, чаты, ошибки, аналитика |
| `mongo` | 27017 | MongoDB 7.0 — основное хранилище |
| `redis` | 6379 | Redis 7.4 — кеш, квоты, сессии |
| `nginx` | 80 | Обратный прокси, роутинг, rate limiting |

### Маршрутизация Nginx

| URL | Сервис |
|---|---|
| `/webhook/telegram` | `bot:8001` |
| `/miniapp/*`, `/auth/*` | `miniapp:8002` |
| `/graphql` | `backend:8000` |
| `/dashboard/*` | `dashboard:8003` |
| `/static/*`, `/health` | `backend:8000` |
| `/*` (остальное) | `backend:8000` |

### Базы данных MongoDB

| База | Используется |
|---|---|
| `ncfu_schedule` | Расписание: пары, группы, преподаватели, аудитории |
| `ncfu_auth` | Пользователи, роли, токены, тикеты, логи ошибок |

---

## Стек технологий

### Backend (Python)
- **FastAPI** + **Uvicorn** + **uvloop** — ASGI веб-сервер
- **Strawberry GraphQL** — GraphQL API для расписания
- **Beanie** + **Motor** — асинхронный ODM для MongoDB
- **Redis** (hiredis) — кеш и квоты запросов
- **httpx** + **BeautifulSoup4** + **lxml** — веб-скрапер расписания
- **APScheduler** — периодический парсинг (каждые N часов)
- **Pydantic v2** + **pydantic-settings** — валидация и конфиг

### Telegram Bot
- **aiogram 3** — асинхронный Telegram Bot Framework
- **OpenAI** + **instructor** — NLU: извлечение интента и параметров из текста
- **rapidfuzz** — нечёткий поиск групп и преподавателей

### Mini App (Frontend)
- **React 18** + **TypeScript** — SPA
- **Vite** — сборщик
- **Apollo Client** + **graphql** — GraphQL запросы

### Безопасность и наблюдаемость
- **PyJWT** + **bcrypt** + **pyotp** — JWT авторизация, 2FA
- **Sentry SDK** — трекинг ошибок
- **OpenTelemetry** + **Prometheus** — метрики
- **Loguru** + **structlog** — логирование

### Инфраструктура
- **Docker** + **Docker Compose** — контейнеризация
- **Nginx 1.27** — прокси, gzip, rate limiting, security headers

---

## Первый деплой (с нуля)

### Требования к серверу
- Ubuntu 20.04+ / Debian 11+
- Docker ≥ 24.0, Docker Compose ≥ 2.20
- 2 GB RAM минимум (рекомендуется 4 GB)
- Открытые порты: 80 (nginx), 443 (если HTTPS через внешний прокси)
- Домен с SSL (Telegram требует HTTPS для webhook)

### Шаг 1 — Клонировать репозиторий

```bash
git clone https://github.com/your/repo.git /opt/ncfu
cd /opt/ncfu
```

### Шаг 2 — Настроить секреты

```bash
sudo bash setup-secrets.sh
```

Скрипт интерактивно спросит все ключи и сохранит их в `/etc/ncfu/secrets` (права `600`, только `root`). Секреты **не хранятся в репозитории** и **переживают перезагрузку**.

Что нужно иметь заранее — смотри раздел [Получение секретных ключей](#получение-секретных-ключей).

### Шаг 3 — Запустить стек

```bash
sudo bash deploy.sh
# или через Make:
make up
```

Первый запуск: Docker скачает образы, соберёт контейнеры, запустит MongoDB/Redis, поднимет все сервисы.

### Шаг 4 — Проверить

```bash
make status    # все контейнеры должны быть Up
make health    # health-check по HTTP каждого сервиса
```

---

## Получение секретных ключей

### TELEGRAM_BOT_TOKEN

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. `/newbot` → дай имя и username боту
3. Скопируй токен вида `123456789:AAF...`

### TELEGRAM_WEBHOOK_SECRET

Случайная строка для верификации webhook-запросов от Telegram. Генерируется автоматически `setup-secrets.sh`, либо вручную:

```bash
openssl rand -hex 32
```

### WEBHOOK_BASE_URL

Публичный HTTPS-домен твоего сервера, например:
```
https://bot.example.com
```
Telegram будет слать обновления на `https://bot.example.com/webhook/telegram`.

> **Важно:** Telegram принимает только HTTPS с валидным сертификатом (Let's Encrypt подходит).

### OPENAI_API_KEY

1. Зайди на [platform.openai.com](https://platform.openai.com)
2. API Keys → Create new secret key
3. Скопируй ключ вида `sk-proj-...`

Используется для NLU — понимания запросов пользователей на естественном языке.

### JWT_SECRET

Используется для подписи токенов авторизации. **Должен быть одинаковым** во всех сервисах (backend, bot, miniapp, dashboard). Генерируется автоматически:

```bash
openssl rand -hex 64
```

### DASHBOARD_SECRET / GRAPHQL_SECRET

Внутренние секреты для аутентификации в админ-панели и GraphQL IDE. Генерируются автоматически `setup-secrets.sh`.

### SUPPORT_BOT_TOKEN (опционально)

Отдельный бот для уведомлений об обращениях в поддержку. Создаётся так же через @BotFather. Если не нужен — оставь пустым.

### SUPPORT_ADMIN_CHAT_ID (опционально)

ID чата/пользователя куда слать уведомления о тикетах поддержки. Узнать свой ID: [@userinfobot](https://t.me/userinfobot).

### SENTRY_DSN (опционально)

1. Зарегистрируйся на [sentry.io](https://sentry.io)
2. Создай проект → Platform: Python / FastAPI
3. Скопируй DSN вида `https://abc@o123.ingest.sentry.io/456`

---

## Переменные окружения

Все переменные задаются через `/etc/ncfu/secrets` на сервере (загружаются `deploy.sh`).
Для локальной разработки — через `.env` файл:

```bash
cp .env.example .env
# Заполни все CHANGE_ME поля
```

| Переменная | Обязательна | Описание |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Токен основного бота |
| `WEBHOOK_BASE_URL` | ✅ | Публичный HTTPS домен |
| `OPENAI_API_KEY` | ✅ | OpenAI для AI-обработки запросов |
| `JWT_SECRET` | ✅ | Секрет для JWT-токенов (одинаковый везде) |
| `MONGO_USER` | ✅ | Пользователь MongoDB |
| `MONGO_PASSWORD` | ✅ | Пароль MongoDB (только a-z A-Z 0-9) |
| `MONGO_DB` | ✅ | Имя БД расписания (по умолч. `ncfu_schedule`) |
| `AUTH_MONGO_DB` | ✅ | Имя БД авторизации (по умолч. `ncfu_auth`) |
| `REDIS_PASSWORD` | ✅ | Пароль Redis (только a-z A-Z 0-9) |
| `DASHBOARD_SECRET` | ✅ | Секрет входа в дашборд |
| `GRAPHQL_SECRET` | ✅ | Секрет для GraphQL IDE |
| `TELEGRAM_WEBHOOK_SECRET` | ✅ | Подпись webhook-запросов |
| `ADMIN_PATH` | — | Путь к дашборду (по умолч. `admin`) |
| `CORS_ALLOWED_ORIGINS` | — | Домены через запятую |
| `BASE_URL` | — | URL eCampus для скрапера |
| `SCRAPE_INTERVAL_HOURS` | — | Интервал парсинга в часах (по умолч. `1`) |
| `SUPPORT_BOT_TOKEN` | — | Бот уведомлений поддержки |
| `SUPPORT_ADMIN_CHAT_ID` | — | Chat ID для уведомлений |
| `SENTRY_DSN` | — | DSN для Sentry |
| `APP_ENV` | — | `production` или `development` |

> **Пароли MongoDB и Redis** должны содержать **только буквы и цифры** — спецсимволы (`@`, `#`, `!`) ломают строку подключения в URL.

---

## Управление стеком — Makefile

```bash
make             # показать все команды
```

### Запуск и остановка

```bash
make up          # поднять весь стек
make stop        # остановить (контейнеры сохранятся)
make down        # остановить и удалить контейнеры
make restart     # перезапустить без пересборки
```

### Обновление

```bash
make pull                   # git pull + пересборка образов + рестарт
make build bot              # пересобрать и перезапустить только бота
make build backend miniapp  # несколько сервисов сразу
```

### Мониторинг

```bash
make status              # статус всех контейнеров
make health              # HTTP health-check каждого сервиса
make logs bot            # логи бота (tail -f)
make logs miniapp n=500  # последние 500 строк
make logs                # логи всего стека
```

### Доступ к базам данных

```bash
make mongo       # MongoDB shell (mongosh)
make redis       # Redis CLI
make shell bot   # bash/sh внутри контейнера бота
```

### Полный сброс (⚠️ удаляет все данные)

```bash
make fresh       # пересоздаёт MongoDB volume с нуля, запрашивает подтверждение
```

---

## deploy.sh — детали

`deploy.sh` — единственная точка деплоя. Загружает секреты из `/etc/ncfu/secrets`, проверяет их наличие и запускает Docker Compose.

```bash
sudo bash deploy.sh              # запуск/обновление стека
sudo bash deploy.sh build bot    # пересобрать один сервис
sudo bash deploy.sh pull         # git pull + rebuild + restart
sudo bash deploy.sh restart      # рестарт без пересборки
sudo bash deploy.sh logs bot     # логи сервиса
sudo bash deploy.sh status       # статус контейнеров
sudo bash deploy.sh stop         # остановить
sudo bash deploy.sh down         # остановить и удалить
sudo bash deploy.sh fresh        # полный сброс (УДАЛЯЕТ данные MongoDB!)
```

**Как работает:**
1. Проверяет наличие `/etc/ncfu/secrets`
2. Проверяет что все обязательные переменные (`MONGO_PASSWORD`, `REDIS_PASSWORD`, `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `JWT_SECRET`) заданы
3. Валидирует пароли на отсутствие спецсимволов
4. Создаёт Docker network `ncfu_network` и volume `ncfu_mongo_data` если их нет
5. Запускает `docker compose`

---

## API Reference

### Backend — REST (:8000)

```
GET  /health
GET  /api/groups
GET  /api/teachers
GET  /api/rooms
GET  /api/institutes
GET  /api/schedules?group=&teacher=&room=&date=
GET  /api/search?q=
GET  /api/overview
POST /api/scrape              (требует admin JWT)
```

### Backend — GraphQL (:8000/graphql)

Основной интерфейс — бот и miniapp работают через него.

```graphql
query {
  groupSchedule(groupName: "ИСС-б-о-22-3", from: "2025-09-01", to: "2025-09-07") {
    date
    lessons { timeStart timeEnd subject teacher room }
  }
  teacherSchedule(teacherName: "Подзолко", from: "2025-09-01") { ... }
  roomSchedule(roomName: "305", building: "2", from: "2025-09-01") { ... }
  freeRooms(building: "11", at: "14:00") { roomName building floor }
  search(q: "ИСС") {
    groups { id name institute }
    teachers { id name }
  }
}
```

GraphQL IDE доступен по `/graphql` при наличии заголовка `X-Admin-Secret`.

### Bot Webhook (:8001)

```
POST /webhook/telegram
GET  /health
```

### Mini App API (:8002)

```
POST   /miniapp/auth
GET    /miniapp/api/profile/limits
GET    /miniapp/api/favorites
POST   /miniapp/api/favorites
DELETE /miniapp/api/favorites/{id}
GET    /miniapp/api/settings
POST   /miniapp/api/settings
POST   /miniapp/api/support
GET    /miniapp
GET    /health
```

### Dashboard API (:8003)

```
GET  /dashboard/admin
GET  /dashboard/me
GET  /dashboard/api/admin/users
GET  /dashboard/api/admin/chats
GET  /dashboard/api/feedback?rating=&status=&search=
GET  /dashboard/api/feedback/stats
GET  /dashboard/api/admin/support?status=
POST /dashboard/api/admin/support/{id}/reply
POST /dashboard/api/admin/support/{id}/close
GET  /dashboard/api/admin/logs/errors?error_id=&search=&level=
GET  /dashboard/api/admin/logs/activity
GET  /dashboard/api/admin/analytics?days=
GET  /health
```

---

## Структура репозитория

```
/
├── backend/                   # REST API + GraphQL + Scraper
│   ├── app/
│   │   ├── api/routes/        # REST эндпоинты
│   │   ├── graphql/           # Schema, resolvers, types
│   │   ├── dashboard/         # Админ-панель: роутер, API, HTML-шаблон
│   │   ├── models/            # Beanie ODM (расписание)
│   │   ├── scraper/           # Парсер ecampus.ncfu.ru
│   │   ├── scheduler/         # Периодический запуск скрапера
│   │   ├── auth/              # JWT, RBAC, модели
│   │   └── core/              # Config, logging, observability
│   ├── Dockerfile
│   └── requirements.txt
│
├── ecampus_bot/               # Telegram Bot
│   ├── app/bot/
│   │   ├── handlers/
│   │   │   ├── commands.py    # /start /help /roles /suggest /about /support /limit
│   │   │   └── ai_handler.py  # NLU → GraphQL → ответ пользователю
│   │   ├── middlewares/
│   │   │   ├── anti_flood.py  # Rate limiting + квоты запросов
│   │   │   └── webhook_ratelimit.py
│   │   ├── router.py          # Регистрация хендлеров, callback-кнопки
│   │   ├── intents.py         # Типы интентов
│   │   └── message_store.py   # Сохранение переписки в MongoDB
│   ├── Dockerfile
│   └── requirements.txt
│
├── miniapp/                   # Telegram Mini App
│   ├── app/miniapp/
│   │   ├── router.py          # API эндпоинты
│   │   ├── quota_service.py   # Лимиты запросов
│   │   └── auth.py            # Валидация Telegram initData
│   └── react-src/src/
│       ├── pages/             # SchedulePage, RoomsPage, FavoritesPage, ProfilePage
│       ├── components/
│       └── types/
│
├── dashboard2/                # Админ-панель (основная)
│   └── app/dashboard/
│       ├── templates/admin.html  # React SPA: аналитика, чаты, отзывы, ошибки
│       └── api_chats.py
│
├── nginx/
│   ├── nginx.conf.template
│   └── entrypoint.sh
│
├── docker-compose.yml         # Полный стек
├── docker-compose.dev.yml     # Dev-оверрайд
├── deploy.sh                  # Деплой (читает /etc/ncfu/secrets)
├── setup-secrets.sh           # Интерактивная настройка секретов
├── Makefile                   # Удобные алиасы для deploy.sh
├── ncfu.service               # systemd unit
└── .env.example               # Шаблон переменных
```

---

## Обновление и CI

### Ручное обновление

```bash
cd /opt/ncfu
make pull
# = git pull + docker compose build --pull + docker compose up -d
```

### Обновление одного сервиса

```bash
make build bot       # только бот
make build miniapp   # только miniapp
make build backend dashboard  # несколько
```

### Workflow

```bash
# Локально: внёс изменения
git add .
git commit -m "feat: ..."
git push origin main

# На сервере:
make pull
```

### GitHub Actions (пример)

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: cd /opt/ncfu && make pull
```

---

## Автозапуск через systemd

Стек автоматически поднимается после перезагрузки сервера.

```bash
# Установить
sudo cp ncfu.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ncfu
sudo systemctl start ncfu

# Управление
sudo systemctl status ncfu
sudo systemctl restart ncfu

# Логи
journalctl -u ncfu -f
```

---

## Troubleshooting

### Контейнер не стартует

```bash
make logs bot      # смотри ошибки при старте
make status        # проверь статус
```

### MongoDB не принимает подключение

Пароли MongoDB и Redis должны содержать **только буквы и цифры** — спецсимволы ломают URI подключения.

```bash
sudo bash setup-secrets.sh   # переустановить пароли
make fresh                    # ⚠️ пересоздать MongoDB volume
```

### Telegram webhook не работает

```bash
# Проверить что бот зарегистрировал webhook:
make logs bot | grep webhook

# Вручную через Telegram API:
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

Нужен HTTPS с валидным сертификатом. Домен в `WEBHOOK_BASE_URL` должен совпадать с реальным.

### Лимиты запросов не применяются

Лимит задаётся в профиле пользователя (поле `daily_requests` в `AuthUser`). Вступает в силу при следующем запросе — сбрасывать Redis вручную не нужно.

### Проверить Redis вручную

```bash
make redis
# Внутри redis-cli:
KEYS quota:*              # активные квоты
GET quota:123456789       # квота пользователя (tg_id)
DEL quota:123456789       # сбросить квоту вручную
```

### Посмотреть данные в MongoDB

```bash
make mongo
# Внутри mongosh:
use ncfu_auth
db.auth_users.findOne({tg_id: 123456789})
db.support_tickets.find({status: "open"}).limit(5)
db.auth_error_logs.find({level: "ERROR"}).sort({timestamp: -1}).limit(10)
```

### Dev-режим с Mongo Express

```bash
docker compose --profile dev up -d
# Mongo Express: http://localhost:8081
```
