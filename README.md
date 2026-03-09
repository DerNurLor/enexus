# NCFU Schedule — Monorepo

Три независимых сервиса, которые деплоятся отдельно, но работают через общие MongoDB и Redis.

```
.
├── backend/        GraphQL API, REST, Dashboard, Scraper, Scheduler  → :8000
├── ecampus_bot/    Telegram бот (webhook, AI-обработка сообщений)    → :8001
├── miniapp/        Telegram Mini App (SPA + API)                     → :8002
├── docker-compose.yml   Запуск всего одной командой
└── .env.example         Шаблон переменных окружения
```

## Быстрый старт

```bash
cp .env.example .env
# Заполнить все CHANGE_ME поля в .env

docker compose up -d
# backend    → http://localhost:8000
# bot        → http://localhost:8001  (webhook: /webhook/telegram)
# miniapp    → http://localhost:8002/miniapp
```

### Dev-режим (+ Mongo Express на :8081)
```bash
docker compose --profile dev up -d
```

### Только отдельный сервис
```bash
docker compose up -d backend          # только API
docker compose up -d bot              # только бот
docker compose logs -f bot            # логи бота
docker compose restart miniapp        # перезапуск
```

## Сервисы

### backend (:8000)
- `POST /graphql` — основной интерфейс расписания
- `GET /health`
- `GET /admin` — дашборд (требует JWT admin)
- `POST /auth/telegram/login`
- Scraper + Scheduler (периодически тянет расписание с ecampus.ncfu.ru)

### ecampus_bot (:8001)
- `POST /webhook/telegram` — принимает обновления от Telegram
- `GET /health`
- Обращается к backend GraphQL по HTTP (`BACKEND_GRAPHQL_URL`)

### miniapp (:8002)
- `GET /miniapp` — SPA
- `POST /miniapp/auth` — Telegram initData → JWT
- `GET /miniapp/api/*` — расписание, поиск, избранное

## Nginx (рекомендуется)

```nginx
# Проксируй к каждому сервису
location /graphql    { proxy_pass http://127.0.0.1:8000; }
location /admin      { proxy_pass http://127.0.0.1:8000; }
location /auth       { proxy_pass http://127.0.0.1:8000; }
location /webhook    { proxy_pass http://127.0.0.1:8001; }
location /miniapp    { proxy_pass http://127.0.0.1:8002; }
```

## Переменные окружения

Все три сервиса читают одни и те же ключевые переменные:
- `JWT_SECRET` — **должен быть одинаковым** во всех трёх сервисах
- `TELEGRAM_BOT_TOKEN` — нужен и боту и миниаппу (для валидации initData)
- `MONGO_*`, `REDIS_*` — shared инфраструктура

Подробности: `.env.example`
