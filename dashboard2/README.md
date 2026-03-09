# NCFU Dashboard — Standalone Service

Независимый дашборд-сервис для администрирования NCFU Schedule.

## Архитектура

```
Backend (порт 8000)  ──┐
                        ├── MongoDB (ncfu_schedule + ncfu_auth)
Dashboard (порт 8003) ──┤
                        └── Redis
```

Dashboard **не имеет собственной БД** — он подключается к тем же MongoDB/Redis, что и Backend.

## Быстрый старт

```bash
cp .env.example .env
# Заполни .env, убедись что JWT_SECRET совпадает с Backend

docker compose up -d
```

Открой `http://localhost:8003/dashboard/admin?secret=<DASHBOARD_SECRET>`

## Настройка в связке с Backend

Если Backend уже запущен через свой docker-compose, Dashboard подключится к той же docker-сети `ncfu_network`. Убедись что:
- `MONGO_HOST=mongo` (имя сервиса Mongo в docker сети)
- `REDIS_HOST=redis` (имя сервиса Redis в docker сети)
- `JWT_SECRET` — одинаковый во всех сервисах

## Безопасность

- Все `/dashboard/api/admin/*` требуют JWT-токен с пермиссией `admin:full`
- `dashboard_secret` в URL — только bootstrap для первого входа
- `admin_path` — дополнительная обфускация пути (defence-in-depth)
- MongoDB операторы заблокированы во всех filter-полях
- Rate-limiting через Redis

## Порты

| Сервис    | Порт |
|-----------|------|
| Dashboard | 8003 |
