# 🛠 Developer Guide

> Руководство разработчика: локальный запуск, структура кода, разработка новых фич, деплой и CI/CD.

---

## Содержание

- [Требования](#требования)
- [Локальный запуск](#локальный-запуск)
- [Структура проекта](#структура-проекта)
- [Конфигурация](#конфигурация)
- [Работа с ботом](#работа-с-ботом)
- [Работа с backend и GraphQL](#работа-с-backend-и-graphql)
- [Работа с Mini App (Frontend)](#работа-с-mini-app-frontend)
- [Работа с базами данных](#работа-с-базами-данных)
- [Добавление нового интента](#добавление-нового-интента)
- [Добавление команды бота](#добавление-команды-бота)
- [Первый деплой на сервер](#первый-деплой-на-сервер)
- [Рабочий процесс обновления](#рабочий-процесс-обновления)
- [CI/CD через GitHub Actions](#cicd-через-github-actions)
- [Systemd автозапуск](#systemd-автозапуск)
- [Мониторинг и логи](#мониторинг-и-логи)
- [Чек-лист разработчика](#чек-лист-разработчика)

---

## Требования

### Для локальной разработки

| Инструмент | Версия | Установка |
|---|---|---|
| Python | 3.11+ | [python.org](https://python.org) |
| Docker | 24.0+ | [docker.com](https://docker.com) |
| Docker Compose | 2.20+ | входит в Docker Desktop |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) (только для frontend) |
| Git | любая | |

### Для продакшн сервера

- Ubuntu 20.04+ / Debian 11+
- 2 GB RAM (рек. 4 GB), 20 GB диска
- Docker 24.0+, Docker Compose 2.20+
- Домен с SSL (Let's Encrypt)

---

## Локальный запуск

### Шаг 1 — Клонировать репозиторий

```bash
git clone https://github.com/your/ncfu-bot.git
cd ncfu-bot
```

### Шаг 2 — Создать `.env` файл

```bash
cp .env.example .env
```

Минимальный набор для локального запуска:

```bash
# .env — локальная разработка
APP_ENV=development

# MongoDB
MONGO_USER=ncfu_app
MONGO_PASSWORD=localpassword123
MONGO_DB=ncfu_schedule
AUTH_MONGO_DB=ncfu_auth

# Redis
REDIS_PASSWORD=localredis123

# Telegram (нужен реальный токен даже локально)
TELEGRAM_BOT_TOKEN=123456789:AAF...
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io
TELEGRAM_WEBHOOK_SECRET=any_random_string_here

# OpenAI
OPENAI_API_KEY=sk-proj-...

# JWT (любая длинная строка)
JWT_SECRET=local_dev_secret_change_in_prod
GRAPHQL_SECRET=local_graphql_secret

# Опционально
SUPPORT_BOT_TOKEN=
SUPPORT_ADMIN_CHAT_ID=0
SENTRY_DSN=
```

> [!WARNING]
> `MONGO_PASSWORD` и `REDIS_PASSWORD` должны содержать **только буквы и цифры** (a-z, A-Z, 0-9). Спецсимволы ломают URI подключения.

### Шаг 3 — Запустить стек

```bash
make up
```

Первый запуск займёт 2–3 минуты (скачивание образов, сборка).

### Шаг 4 — Проверить здоровье сервисов

```bash
make health
# Expected:
#   ✓ backend  :8000 — ok
#   ✓ bot      :8001 — ok
#   ✓ miniapp  :8002 — ok
```

### Шаг 5 — Настроить Telegram webhook (для разработки)

Для локального получения webhook-обновлений нужен публичный URL (ngrok или аналог):

```bash
# Установить ngrok (https://ngrok.com)
ngrok http 8080

# Скопировать URL вида: https://abc123.ngrok.io
# Обновить WEBHOOK_BASE_URL в .env

# Зарегистрировать webhook у Telegram:
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://abc123.ngrok.io/webhook/telegram",
       "secret_token": "any_random_string_here"}'

# Проверить:
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo"
```

### Dev-профиль с Mongo Express

```bash
# Mongo Express для браузерного просмотра БД:
docker compose --profile dev up -d

# Открыть: http://localhost:8081
```

---

## Структура проекта

```
/
├── backend/                    # REST API + GraphQL + Scraper
│   ├── app/
│   │   ├── api/routes/         # REST эндпоинты
│   │   │   ├── groups.py       # GET /api/groups
│   │   │   ├── teachers.py     # GET /api/teachers
│   │   │   ├── rooms.py        # GET /api/rooms
│   │   │   ├── search.py       # GET /api/search/* (14 эндпоинтов)
│   │   │   ├── schedules.py    # GET /api/schedules
│   │   │   ├── institutes.py   # GET /api/institutes
│   │   │   ├── overview.py     # GET /api/overview
│   │   │   └── scrape.py       # POST /api/scrape
│   │   ├── graphql/
│   │   │   ├── schema.py       # Query, Mutation, Subscription + защиты
│   │   │   ├── resolvers.py    # Логика резолверов
│   │   │   └── types.py        # Strawberry типы
│   │   ├── scraper/
│   │   │   ├── scraper.py      # NCFUScraper — 3-фазный пайплайн
│   │   │   ├── client.py       # NCFUClient — HTTP-клиент к eCampus
│   │   │   └── parser.py       # parse_institute, parse_group, parse_week
│   │   ├── scheduler/
│   │   │   └── scheduler.py    # APScheduler: hourly_scrape + daily_cleanup
│   │   ├── models/             # Beanie ODM (ncfu_schedule БД)
│   │   │   ├── lesson.py       # LessonDoc — основная коллекция
│   │   │   ├── group.py        # Group
│   │   │   ├── teacher.py      # Teacher
│   │   │   ├── room.py         # Room
│   │   │   └── institute.py    # Institute
│   │   ├── auth/               # JWT, RBAC, модели пользователей
│   │   ├── core/               # Config, logging, observability
│   │   └── main.py             # FastAPI app factory
│   ├── Dockerfile
│   └── requirements.txt
│
├── ecampus_bot/                # Telegram Bot
│   ├── app/
│   │   ├── bot/
│   │   │   ├── handlers/
│   │   │   │   ├── ai_handler.py   # NLU → GraphQL → format → send
│   │   │   │   └── commands.py     # /start /help /roles /support /suggest...
│   │   │   ├── middlewares/
│   │   │   │   ├── anti_flood.py   # AntiFloodMiddleware + MessageLimitMiddleware
│   │   │   │   └── webhook_ratelimit.py
│   │   │   ├── router.py           # Регистрация всех хендлеров
│   │   │   ├── intents.py          # 12 Intent Pydantic-моделей
│   │   │   ├── conversation.py     # Управление историей диалога
│   │   │   ├── message_store.py    # Сохранение переписки в MongoDB
│   │   │   └── utils/bot_send.py   # Утилиты отправки
│   │   ├── auth/                   # Модели пользователей (ncfu_auth)
│   │   └── core/                   # Config, logging
│   ├── Dockerfile
│   └── requirements.txt
│
├── miniapp/                    # Telegram Mini App
│   ├── app/miniapp/
│   │   ├── router.py           # FastAPI API для SPA
│   │   ├── auth.py             # Валидация Telegram initData
│   │   └── quota_service.py    # Лимиты запросов
│   └── react-src/              # React SPA (TypeScript + Vite)
│       └── src/
│           ├── App.tsx
│           ├── pages/          # SchedulePage RoomsPage FavoritesPage ProfilePage
│           ├── components/     # Icons Toast
│           ├── hooks/          # useTheme useToast
│           └── utils/
│               ├── api.ts      # API-клиент с auto-reauth
│               └── helpers.ts
│
├── nginx/
│   ├── nginx.conf.template    # Шаблон с ${NGINX_ADMIN_PATH}
│   └── entrypoint.sh          # envsubst → nginx -g daemon off
│
├── docker-compose.yml         # Основной стек
├── docker-compose.dev.yml     # Dev-оверрайд (mongo-express)
├── deploy.sh                  # Деплой (читает /etc/ncfu/secrets)
├── setup-secrets.sh           # Интерактивная настройка секретов
├── Makefile                   # Алиасы
├── ncfu.service               # Systemd unit
└── .env.example               # Шаблон переменных
```

---

## Конфигурация

### Как работает конфигурация

Каждый сервис имеет свой `app/core/config.py` с `pydantic-settings`:

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Обычные переменные — читаются из env
    app_env: str = "development"
    mongo_db: str = "ncfu_schedule"

    # Секреты — никогда не попадают в repr и логи
    jwt_secret: SecretStr = SecretStr("")
    openai_api_key: SecretStr

settings = Settings()  # singleton, читается один раз при импорте
```

**Приоритет:** переменные окружения → `.env` файл → значения по умолчанию

### Ключевые настройки

| Переменная | Где используется | Важность |
|---|---|---|
| `JWT_SECRET` | Все 4 сервиса | 🔴 ОДИНАКОВЫЙ везде |
| `TELEGRAM_BOT_TOKEN` | bot, miniapp | 🔴 Обязательный |
| `OPENAI_API_KEY` | bot | 🔴 Обязательный |
| `MONGO_PASSWORD` | Все сервисы | 🔴 Только a-z0-9 |
| `REDIS_PASSWORD` | Все сервисы | 🔴 Только a-z0-9 |
| `WEBHOOK_BASE_URL` | bot, miniapp | 🔴 HTTPS домен |
| `quota_private` | bot middleware | 🟡 Дефолт лимит ЛС |
| `scrape_interval_hours` | backend scheduler | 🟡 Частота парсинга |

---

## Работа с ботом

### Добавление команды бота

1. **Написать handler в `commands.py`:**

```python
async def cmd_status(message: Message) -> None:
    """Показать статус системы."""
    await message.answer(
        "✅ Система работает нормально\n"
        f"Версия: 2.0",
        parse_mode="HTML",
    )
```

2. **Зарегистрировать в `router.py`:**

```python
from app.bot.handlers.commands import cmd_status

@router.message(Command("status"))
async def handle_status(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message, role="user"))
    await cmd_status(message)
```

3. **Добавить в список команд `BOT_COMMANDS`:**

```python
BOT_COMMANDS = [
    ...
    BotCommand(command="status", description="Статус системы"),
]
```

4. **Добавить в список exempt (если не должна тратить квоту):**

```python
# anti_flood.py
_EXEMPT_COMMANDS = frozenset({
    "/start", "/help", ..., "/status",  # ← добавить
})
```

5. **Пересобрать и перезапустить:**

```bash
make build bot
```

---

## Работа с backend и GraphQL

### Добавление REST-эндпоинта

```python
# backend/app/api/routes/overview.py
from fastapi import APIRouter
router = APIRouter(prefix="/overview", tags=["Overview"])

@router.get("/")
async def get_overview():
    total_groups = await Group.count()
    return {"total_groups": total_groups}
```

```python
# backend/app/main.py — зарегистрировать роутер
from app.api.routes.overview import router as overview_router
app.include_router(overview_router, prefix="/api")
```

### Добавление GraphQL Query

```python
# backend/app/graphql/schema.py
@strawberry.type
class Query:
    @strawberry.field(description="Count total groups")
    async def total_groups(self) -> int:
        return await R.resolve_total_groups()
```

```python
# backend/app/graphql/resolvers.py
async def resolve_total_groups() -> int:
    return await LessonDoc.distinct("group_id").__len__()
```

---

## Работа с Mini App (Frontend)

### Локальная разработка React SPA

```bash
cd miniapp/react-src

npm install
npm run dev  # Dev server на http://localhost:3000

# SPA будет проксировать API запросы на miniapp:8002
# (настройка в vite.config.ts)
```

### Сборка и деплой

```bash
cd miniapp/react-src
npm run build

# Скопировать артефакты:
cp -r dist/* ../app/miniapp/static/

# Пересобрать Docker-образ:
cd ../..
make build miniapp
```

### Структура React-приложения

```
react-src/src/
├── App.tsx           # Роутинг между страницами, авторизация
├── pages/
│   ├── SchedulePage.tsx  # Основная страница расписания
│   ├── RoomsPage.tsx     # Свободные аудитории
│   ├── FavoritesPage.tsx # Избранное
│   └── ProfilePage.tsx   # Профиль и настройки
├── utils/
│   ├── api.ts        # Все API-запросы + auto-reauth при 401
│   └── helpers.ts    # Форматирование дат, времени
├── hooks/
│   ├── useTheme.ts   # Системная/пользовательская тема
│   └── useToast.ts   # Toast-уведомления
└── types/index.ts    # TypeScript интерфейсы (Lesson, Day, User...)
```

---

## Работа с базами данных

### MongoDB shell

```bash
make mongo

# Примеры запросов:
use ncfu_auth
db.auth_users.findOne({tg_id: 123456789})
db.support_tickets.find({status: "open"}).sort({created_at: -1}).limit(5)
db.auth_error_logs.find({level: "ERROR"}).sort({timestamp: -1}).limit(10)
db.bot_feedback.aggregate([
    {$group: {_id: "$rating", count: {$sum: 1}}}
])

use ncfu_schedule
db.lessons.findOne({group_name: "ИСС-б-о-22-3"})
db.groups.countDocuments()
```

### Redis CLI

```bash
make redis

# Примеры:
KEYS quota:*                     # все активные квоты
GET quota:123456789              # квота пользователя
TTL quota:123456789              # сколько секунд до сброса
DEL quota:123456789              # сбросить квоту

KEYS gql:*                       # GraphQL кеш
TTL gql:abc123                   # TTL кеша

KEYS bot:pages:*                 # пагинация ответов
```

### Миграции данных

В `backend/app/scripts/` есть скрипты миграции:

```bash
# Запустить миграцию внутри контейнера:
docker compose exec backend python -m app.scripts.migrate_conversation
```

---

## Добавление нового интента

Допустим, нужно добавить интент `ExamScheduleIntent` — «расписание экзаменов».

### 1. Добавить Pydantic-модель в `intents.py`

```python
class ExamScheduleIntent(BaseModel):
    """User wants the exam schedule for a group."""
    intent: Literal["exam_schedule"] = "exam_schedule"
    group_name: Optional[str] = Field(None, description="Group name")
    from_date: Optional[str] = None
    to_date: Optional[str] = None

# Добавить в Union:
AnyIntent = Annotated[
    Union[
        ...,
        ExamScheduleIntent,  # ← добавить
        UnknownIntent,
    ],
    Field(discriminator="intent"),
]
```

### 2. Добавить GraphQL-запрос в `ai_handler.py`

```python
_GQL_EXAM_SCHEDULE = """
query ExamSchedule($gn: String, $from: String, $to: String) {
  examSchedule(groupName: $gn, fromDate: $from, toDate: $to) {
    date lessons { timeStart subject examType roomName }
  }
}
"""
```

### 3. Добавить обработчик в dispatch-функцию

```python
async def _dispatch(intent, message):
    ...
    elif isinstance(intent, ExamScheduleIntent):
        data = await _gql(_GQL_EXAM_SCHEDULE, {
            "gn": intent.group_name,
            "from": intent.from_date,
            "to": intent.to_date,
        })
        days = data.get("examSchedule", [])
        reply = _fmt_days_paged(days, f"Экзамены · {intent.group_name}",
                                show_teacher=False, show_group=False)
```

### 4. Добавить соответствующий GraphQL resolver в backend

```python
# backend/app/graphql/schema.py
@strawberry.field(description="Exam schedule for a group")
async def exam_schedule(self, group_name: str, ...) -> List[DayType]:
    return await R.resolve_exam_schedule(group_name, ...)
```

---

## Первый деплой на сервер

### Шаг 1 — Подготовить сервер

```bash
# Ubuntu 20.04+
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl

# Установить Docker:
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo systemctl enable docker

# Docker Compose (если не установлен вместе с Docker):
sudo apt install -y docker-compose-plugin
```

### Шаг 2 — Клонировать репозиторий

```bash
sudo git clone https://github.com/your/ncfu-bot.git /opt/ncfu
sudo chown -R $USER:$USER /opt/ncfu
cd /opt/ncfu
```

### Шаг 3 — Настроить секреты

```bash
sudo bash setup-secrets.sh
```

Скрипт спросит:
- `TELEGRAM_BOT_TOKEN` — от @BotFather
- `WEBHOOK_BASE_URL` — ваш HTTPS-домен (например `https://bot.ncfu.ru`)
- `OPENAI_API_KEY` — от platform.openai.com
- Пароли MongoDB и Redis — генерирует автоматически
- JWT_SECRET и другие — генерирует автоматически

> [!TIP]
> Повторный запуск `setup-secrets.sh` показывает текущие значения и позволяет изменить только нужные (пустой ввод = оставить текущее).

### Шаг 4 — Запустить стек

```bash
sudo bash deploy.sh
# или: make up
```

### Шаг 5 — Зарегистрировать webhook

```bash
# Замените TOKEN и URL:
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/webhook/telegram",
    "secret_token": "<TELEGRAM_WEBHOOK_SECRET из /etc/ncfu/secrets>"
  }'
```

### Шаг 6 — Настроить TLS

Nginx внутри стека слушает на порту 80 HTTP. Для HTTPS используйте внешний терминатор:

```bash
# Вариант 1: Caddy (автоматический Let's Encrypt)
sudo apt install caddy
sudo tee /etc/caddy/Caddyfile <<EOF
your-domain.com {
    reverse_proxy localhost:8080
}
EOF
sudo systemctl restart caddy

# Вариант 2: Nginx + certbot
sudo apt install nginx certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
# Затем проксировать на localhost:8080
```

---

## Рабочий процесс обновления

### Обновление всего стека

```bash
cd /opt/ncfu
make pull
# = git pull + docker compose build --pull + docker compose up -d --remove-orphans
```

### Обновление одного сервиса (без даунтайма остальных)

```bash
make build bot        # пересобрать бот
make build miniapp    # пересобрать miniapp
make build backend    # пересобрать backend
```

### Ротация секретов

```bash
sudo bash setup-secrets.sh  # изменить нужные значения
make restart                 # применить новые секреты
```

> [!WARNING]
> Смена `JWT_SECRET` инвалидирует все существующие токены. Пользователям Mini App придётся заново авторизоваться.

---

## CI/CD через GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

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
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/ncfu
            make pull
```

**Секреты для GitHub Actions:**

| Секрет | Значение |
|---|---|
| `SERVER_HOST` | IP или hostname сервера |
| `SERVER_USER` | Пользователь (root или sudo) |
| `SSH_PRIVATE_KEY` | Приватный SSH-ключ |

### Деплой отдельного сервиса при изменении только его файлов

```yaml
# .github/workflows/deploy-selective.yml
jobs:
  detect-changes:
    outputs:
      bot: ${{ steps.changes.outputs.bot }}
      miniapp: ${{ steps.changes.outputs.miniapp }}
    steps:
      - uses: dorny/paths-filter@v2
        id: changes
        with:
          filters: |
            bot:
              - 'ecampus_bot/**'
            miniapp:
              - 'miniapp/**'

  deploy-bot:
    needs: detect-changes
    if: needs.detect-changes.outputs.bot == 'true'
    steps:
      - name: Deploy bot only
        uses: appleboy/ssh-action@v1
        with:
          script: cd /opt/ncfu && make build bot
```

---

## Systemd автозапуск

```bash
# Установить unit:
sudo cp /opt/ncfu/ncfu.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ncfu

# Управление:
sudo systemctl start ncfu
sudo systemctl stop ncfu
sudo systemctl restart ncfu
sudo systemctl status ncfu

# Логи через journald:
journalctl -u ncfu -f
journalctl -u ncfu --since "1 hour ago"
```

---

## Мониторинг и логи

### Просмотр логов

```bash
make logs                  # все сервисы, последние 100 строк, tail -f
make logs bot              # только бот
make logs backend n=200    # последние 200 строк backend
make logs miniapp n=50     # последние 50 строк miniapp

# Прямо через docker compose:
docker compose logs -f --tail=100 bot
docker compose logs --since 1h backend
```

### Health checks

```bash
make health
# Результат:
#   ✓ backend   :8000 — ok
#   ✓ bot       :8001 — ok
#   ✓ miniapp   :8002 — ok

# Отдельный сервис:
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### Prometheus метрики (если включен OTEL_ENDPOINT)

```bash
# Метрики доступны по:
curl http://localhost:8000/metrics
```

### Sentry

Если задан `SENTRY_DSN`, все ошибки автоматически отправляются в Sentry.
Flood-события также трекируются через `capture_message`.

### ERR-ID — трассировка ошибок

Когда бот сталкивается с ошибкой, он генерирует уникальный `ERR-XXXXXX` код и сообщает его пользователю. Этот же код пишется в MongoDB (`auth_error_logs.error_id`).

Ошибки можно найти по ERR-ID в MongoDB (`auth_error_logs.error_id`) или через `make logs`.

---

## ✅ Чек-лист разработчика

После прочтения этого документа вы должны уметь:

- [ ] Поднять полный стек локально за 10 минут
- [ ] Настроить ngrok и зарегистрировать webhook для локальной разработки
- [ ] Добавить новую команду бота от начала до конца
- [ ] Добавить новый GraphQL resolver
- [ ] Собрать и задеплоить изменения в React SPA (miniapp)
- [ ] Подключиться к MongoDB и Redis прямо из терминала
- [ ] Выполнить полный деплой на продакшн сервер с нуля
- [ ] Настроить GitHub Actions для автодеплоя
- [ ] Читать логи и находить ошибки по ERR-ID
