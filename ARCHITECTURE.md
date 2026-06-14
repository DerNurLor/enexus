# 🏗 Architecture

> Архитектурные решения, схемы взаимодействия, потоки данных, AI-пайплайн и обоснование технических выборов.

---

## Содержание

- [Обзор системы](#обзор-системы)
- [Сервисная декомпозиция](#сервисная-декомпозиция)
- [Маршрутизация Nginx](#маршрутизация-nginx)
- [Потоки данных](#потоки-данных)
- [Базы данных](#базы-данных)
- [AI-пайплайн NLU](#ai-пайплайн-nlu)
- [Система квот и rate limiting](#система-квот-и-rate-limiting)
- [Безопасность](#безопасность)
- [Кеширование](#кеширование)
- [Скрапер и планировщик](#скрапер-и-планировщик)
- [GraphQL схема](#graphql-схема)
- [Инфраструктура и деплой](#инфраструктура-и-деплой)
- [Чек-лист разработчика](#чек-лист-разработчика)

---

## Обзор системы

NCFU Schedule Bot — **микросервисная** система из 3 прикладных сервисов на общей инфраструктуре (MongoDB + Redis), за единой точкой входа (Nginx). Каждый сервис — отдельный Docker-контейнер с собственным FastAPI-приложением.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Telegram / Browser / Admin                        │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ HTTPS  (внешний TLS-терминатор или Caddy)
                         ┌──────▼──────┐
                         │    Nginx    │  :80 — единая точка входа
                         │   1.27      │  rate limiting, gzip, security headers
                         └──────┬──────┘
           ┌──────────────────┬─┴──────────────┐
           │                  │                │
    ┌──────▼──────┐   ┌───────▼──────┐ ┌──────▼──────┐
    │   backend   │   │     bot      │ │   miniapp   │
    │    :8000    │◄──│    :8001     │ │    :8002    │
    │             │   │              │ │             │
    │ REST API    │   │ aiogram 3    │ │ FastAPI API │
    │ GraphQL     │   │ OpenAI NLU   │ │ React SPA   │
    │ Scraper     │   │ Webhook      │ │ Mini App    │
    │ Scheduler   │   │ Middleware   │ │             │
    └──────┬──────┘   └──────────────┘ └──────┬──────┘
           │                                   │
           └─────────────────┬─────────────────┘
                             │ shared read/write
              ┌──────────────▼──────────────┐
              │                             │
       ┌──────▼──────┐              ┌───────▼──────┐
       │   MongoDB   │              │    Redis     │
       │    7.0      │              │    7.4       │
       │             │              │              │
       │ ncfu_schedule (расписание) │ Cache TTL    │
       │ ncfu_auth (пользователи)   │ Quotas       │
       └─────────────┘              │ Sessions     │
                                    │ Paged data   │
                                    └──────────────┘
```

---

## Сервисная декомпозиция

### Почему 3 сервиса, а не монолит?

Система выросла из монолита. Декомпозиция решила конкретные проблемы:

1. **bot** загружает aiogram + OpenAI client (~150 MB) — изоляция позволяет перезапускать его без даунтайма API
2. **miniapp** получает всплески трафика от студентов — автономный скейлинг без влияния на других
3. **backend** — единственный владелец данных расписания; остальные обращаются к нему через GraphQL

### Границы ответственности

```
╔═══════════════╦════════════════════════╦═══════════════════════════════╗
║ Сервис        ║ Владеет                ║ Читает через                  ║
╠═══════════════╬════════════════════════╬═══════════════════════════════╣
║ backend       ║ ncfu_schedule DB       ║ ncfu_auth (JWT verify)        ║
║               ║ расписание, scraper    ║                               ║
╠═══════════════╬════════════════════════╬═══════════════════════════════╣
║ bot           ║ ncfu_auth DB           ║ ncfu_schedule через GraphQL   ║
║               ║ users, tickets, errors ║ Redis (quota, cache, pages)   ║
╠═══════════════╬════════════════════════╬═══════════════════════════════╣
║ miniapp       ║ —                      ║ ncfu_schedule через GraphQL   ║
║               ║                        ║ ncfu_auth (профиль, favorites)║
╚═══════════════╩════════════════════════╩═══════════════════════════════╝
```

---

## Маршрутизация Nginx

```nginx
# Nginx маршрутизация (nginx.conf.template):

/webhook/telegram     →  bot:8001       (rate: 100 req/s, Telegram IPs)
/miniapp/*            →  miniapp:8002   (rate: 30 req/min)
/auth/*               →  miniapp:8002   (rate: 10 req/min — auth endpoint)
/graphql              →  backend:8000   (rate: 30 req/min)
/static/*             →  backend:8000   (no rate limit, cached)
/health               →  backend:8000
/*                    →  backend:8000   (REST API)
```

**Rate limiting zones:**

| Зона | Лимит | Применяется к |
|---|---|---|
| `api_limit` | 30 req/min | REST API |
| `webhook_limit` | 100 req/sec | Telegram webhook |
| `auth_limit` | 10 req/min | Auth endpoints |

---

## Потоки данных

### 1. Типичный запрос пользователя через бота

```
User → Telegram → POST /webhook/telegram
                           │
                   bot:8001 (aiogram dispatcher)
                           │
              ┌────────────▼─────────────────┐
              │  Middleware: AntiFloodMiddleware │
              │  (5 msg/min per user, 2× Premium)│
              └────────────┬─────────────────┘
                           │
              ┌────────────▼─────────────────┐
              │  Middleware: MessageLimitMiddleware │
              │  (3 req/7h private, 5 group)  │
              │  Exempt: /start /help /roles… │
              └────────────┬─────────────────┘
                           │
                    Router → ai_handler
                           │
              ┌────────────▼─────────────────┐
              │  1. Hash(user_id + text)       │
              │  2. Redis GET cache_key        │
              │     HIT  → ответ из кеша       │
              │     MISS → продолжить          │
              └────────────┬─────────────────┘
                           │ cache miss
              ┌────────────▼─────────────────┐
              │  3. Build context             │
              │     - конвертировать историю  │
              │     - уточнить текущее время  │
              └────────────┬─────────────────┘
                           │
              ┌────────────▼─────────────────┐
              │  4. OpenAI Instructor         │
              │     → IntentResponse          │
              │     (одна из 12 Intent моделей)│
              └────────────┬─────────────────┘
                           │
              ┌────────────▼─────────────────┐
              │  5. Dispatch intent           │
              │     → GraphQL query           │
              │       backend:8000/graphql    │
              └────────────┬─────────────────┘
                           │
              ┌────────────▼─────────────────┐
              │  6. Format response           │
              │     - если дней > 1 → paginate│
              │     - store pages in Redis    │
              │     - add nav buttons ◀ ▶    │
              │     - add feedback 👍 👎      │
              └────────────┬─────────────────┘
                           │
              ┌────────────▼─────────────────┐
              │  7. Send to Telegram          │
              │  8. store_message() MongoDB   │
              │     (async, non-blocking)     │
              └──────────────────────────────┘
```

### 2. Авторизация в Mini App

```
Telegram Client
       │
       ├── open /miniapp  →  GET /miniapp  →  HTML Shell (React SPA)
       │
       └── SPA init:
              POST /miniapp/auth { init_data: "<Telegram initData>" }
                     │
              1. Validate HMAC-SHA256(init_data, bot_token)
              2. Parse user from init_data
              3. Upsert AuthUser в MongoDB (creates if first visit)
              4. issue JWT(user_id, tg_id, roles, exp=1h)
                     │
              ← { token, user: { roles, permissions, is_beta, ... } }
                     │
              SPA: сохраняет token в памяти (_token variable)
              Все последующие запросы: Authorization: Bearer <token>
              При 401 → auto re-auth через initData (transparent)
```

### 3. Скрапинг и инвалидация кеша

```
APScheduler (каждые N часов)
       │
NCFUScraper.run()
       │
  Phase 1: GET /api/institutes → parse → upsert MongoDB
  Phase 2: GET /api/specialties → GET /api/groups → upsert MongoDB
  Phase 3: Для каждой группы:
              GET ecampus.ncfu.ru/schedule?group=X
              → canonical_hash(new_data)
              → compare with stored_hash
              ├── SAME → skip (0 writes)
              └── DIFF → bulk_replace lessons
                       → Redis invalidate pattern: "gql:*"
```

---

## Базы данных

### Разделение на две БД — намеренное архитектурное решение

```
ncfu_schedule                  ncfu_auth
──────────────                 ────────────────────
lessons          (основная)    auth_users
groups                         auth_roles
teachers                       auth_api_keys
rooms                          auth_activity_log   (TTL: 90 дней)
institutes                     auth_error_logs     (TTL: 30 дней)
schedules                      chat_messages       (TTL: 180 дней)
scrape_logs                    bot_conversations
chat_settings                  support_tickets
conversations                  broadcast_jobs
                               bot_feedback
                               auth_dpop_nonces    (TTL: 10 минут)
```

**Обоснование разделения:**
- `ncfu_schedule` — публичные данные расписания, высоко читаемые, часто обновляемые скрапером
- `ncfu_auth` — приватные данные пользователей (токены, переписка, логи)
- Независимые бекапы и восстановление
- В будущем — вынести на разные реплика-сеты

### Индексирование коллекции `lessons`

Это самая нагруженная коллекция. Все запросы проходят по составным индексам:

```python
# Индексы LessonDoc (в порядке важности):
(date, group_id)          # расписание группы на день
(date, teacher_id)        # расписание преподавателя
(date, room_id)           # загруженность аудитории
(date, time_start)        # диапазонные запросы (свободные аудитории)
(group_id, week_number)   # расписание группы на неделю
(teacher_id, week_number) # расписание преподавателя на неделю
(room_id, week_number)    # расписание аудитории на неделю
text(subject, teacher_name, room_name, group_name)  # full-text search
```

> [!TIP]
> Запрос «свободные аудитории» — самый тяжёлый: агрегация по всем занятым аудиториям в диапазоне времени. Индекс `(date, time_start)` критичен для производительности.

---

## AI-пайплайн NLU

### Архитектура извлечения интента

```python
# Упрощённая схема работы ai_handler.py

user_message = "Где пара через 5 минут у Подзолко?"

# 1. Кеш-проверка (избегаем повторных API-запросов)
cache_key = f"ai:{md5(f'{user_id}:{user_message}')}"
if cached := await redis.get(cache_key):
    return cached  # TTL: 300 сек

# 2. Контекст диалога (последние N сообщений)
history = await get_history(user_id)  # из Redis/MongoDB
system_prompt = build_context_prompt(history, now=moscow_time)

# 3. OpenAI + Instructor → строго типизированный интент
client = instructor.from_openai(AsyncOpenAI(api_key=...))
response: IntentResponse = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": system_prompt},
              *history, {"role": "user", "content": user_message}],
    response_model=IntentResponse,  # Pydantic-валидация ответа
)
# → TeacherNowIntent(teacher_name="Подзолко", time_ref=TimeRef(offset_minutes=5))

# 4. Нормализация данных
teacher_name = "Подзолко"  # передаём verbatim — backend нормализует падежи

# 5. GraphQL-запрос к backend
data = await _gql(GQL_LESSONS_DAY, {day: today, teacher_name: "Подзолко"})

# 6. Форматирование ответа + пагинация если нужно
reply = _fmt_now(teacher_name, "14:05", active_lessons, upcoming_lessons)
```

### Все 12 интентов системы

| Интент | Пример запроса | Действие |
|---|---|---|
| `group_schedule` | «Расписание ИСС-б-о-22-3 на эту неделю» | GraphQL groupSchedule |
| `teacher_schedule` | «Расписание Иванова на завтра» | GraphQL teacherSchedule |
| `group_now` | «Что сейчас у группы АИС-25?» | GraphQL lessonsOn |
| `teacher_now` | «Где Подзолко через 5 минут?» | GraphQL lessonsOn |
| `free_rooms` | «Свободные аудитории в корпусе 11» | GraphQL freeRooms |
| `building_schedule` | «Когда завтра свободен 3 корпус?» | GraphQL lessonsByBuilding |
| `room_schedule` | «Расписание ауд. 11-405» | GraphQL roomSchedule |
| `search` | «Найди группу ИСС» | GraphQL search |
| `lessons_on_day` | «Все пары 15 сентября» | GraphQL lessonsOn |
| `overview` | «Общая статистика» | GraphQL overview |
| `institutes` | «Список институтов» | GraphQL institutes |
| `unknown` | Непонятный запрос | Бот просит уточнить |

### Нормализация названия группы

Студенты пишут группы в десятках форматов. Система приводит их к единому виду:

```python
"исс б о 22 3"   → "ИСС-б-о-22-3"  (пробелы → дефисы)
"ISS-b-o-22-3"   → "ИСС-б-о-22-3"  (транслитерация латиницы)
"аис25"          → "аис-б-о-25"    (короткая форма: год без подгруппы)
"ИСС  Б О 22-3"  → "ИСС-б-о-22-3"  (двойные пробелы, регистр)
"аис222"         → "аис-б-о-22-2"  (3 цифры: год22 + подгруппа2)
```

---

## Система квот и rate limiting

### Схема работы квоты

```
Входящее сообщение
       │
  exempt?  →  /start, /help, /roles, /limit, /support, /suggest, /about, /miniapp
  ├── YES  →  пропустить (quota не тратится)
  └── NO   →
             Определить quota_id:
             ├── private chat  → user.tg_id
             └── group chat    → chat.id

             Определить cap (приоритет):
             1. AuthUser.daily_requests (если задан admin-ом для этого user)
             2. ChatSettings.bot_quota_cap (если задан для этого chat)
             3. Глобальные дефолты из config:
                - private:      quota_private = 3
                - group < 4:    quota_group_small = 3
                - group ≥ 4:    quota_group_large = 5

             Redis: GET quota:{id}
             ├── current >= cap  →  send limit message + return None (block)
             └── current < cap   →  INCR + set TTL 7h
                                    → call handler
                                    → if error: DECR (не считать неудачный запрос)
```

### Уровни rate limiting (снизу вверх)

```
Level 1: Nginx  — IP-based rate limiting
Level 2: AntiFloodMiddleware — 5 msg/min per user (flood protection)
Level 3: MessageLimitMiddleware — 3 req/7h per user/chat (AI quota)
Level 4: FastAPI GlobalRateLimitMiddleware — user/anon RPM
```

---

## Безопасность

### JWT токены

```python
# Создание access token:
payload = {
    "sub":   str(user.id),    # MongoDB ObjectId
    "tg_id": user.tg_id,      # Telegram ID
    "roles": user.roles,      # ["user", "beta"]
    "iat":   now,
    "exp":   now + timedelta(minutes=60),  # 1 час
    "jti":   secrets.token_hex(16),        # уникальный ID для отзыва
}
token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
```

**Важно:** `JWT_SECRET` — единый для всех 4 сервисов, хранится только в `/etc/ncfu/secrets`.

### Telegram Mini App — валидация initData

```python
# Стандартная Telegram валидация (HMAC-SHA256):
data_check_string = "\n".join(
    f"{k}={v}" for k, v in sorted(params.items()) if k != "hash"
)
secret_key = hmac.new(b"WebAppData", bot_token.encode(), sha256).digest()
expected_hash = hmac.new(secret_key, data_check_string.encode(), sha256).hexdigest()

if expected_hash != received_hash:
    raise HTTPException(401, "Invalid Telegram initData")
```

### Telegram Webhook верификация

```python
# В webhook_ratelimit.py:
received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
if received_secret != settings.get_telegram_webhook_secret():
    return Response(status_code=403)  # Drop fake webhook
```

### GraphQL защита от DoS

```python
# schema.py — два расширения:
schema = strawberry.Schema(
    extensions=[
        QueryDepthLimiter,      # max depth = 5 уровней вложенности
        MaxTokensLimiter(1000), # max 1000 токенов в документе
    ]
)
# GraphiQL IDE — только с заголовком X-Admin-Secret
```

### RBAC — роли и права

| Роль | Иконка | Права |
|---|---|---|
| `user` | ⚪ | Базовый доступ к расписанию |
| `beta` | 🔵 | `beta_access` — расширенные фильтры |
| `vip` | 🟡 | Повышенные лимиты [предположение / требует уточнения] |
| `moderator` | 🟠 | Управление тикетами поддержки |
| `admin` | 🔴 | `admin:full` — полный доступ |

**Специальные права:**
- `floorplan:view` — просмотр планов этажей
- `floorplan:edit` — редактирование планов этажей
- `users:read`, `users:write` — управление пользователями
- `logs:read` — просмотр логов

---

## Кеширование

### Слои кеша (Redis)

| Ключ | TTL | Что хранится |
|---|---|---|
| `ai:{md5}` | 300s | Ответы AI (одинаковый запрос = кеш) |
| `gql:{hash}` | 60–900s | GraphQL-ответы (зависит от типа) |
| `bot:pages:{uid}:{h}` | 3600s | Страницы пагинации расписания |
| `disambig:{uid}:{h}` | 300s | Список совпадений для уточнения |
| `flood:{uid}:{bucket}` | window+5s | Счётчики anti-flood |
| `quota:{id}` | 7h (rolling) | Счётчики квот запросов |

### TTL стратегия для GraphQL-кеша

| Тип данных | TTL | Обоснование |
|---|---|---|
| `lessons_now` | 60s | Пары меняются каждые ~90 минут |
| `lessons_day` | 600s | Стабильно в течение дня |
| `lessons_week` | 900s | Практически не меняется |
| `search` | 300s | Баланс свежести и нагрузки |
| `overview` | 300s | Статистика — не real-time |
| `meta` (институты, группы) | 3600s | Меняется редко |

---

## Скрапер и планировщик

### 3-фазный пайплайн

```
Phase 1 — INSTITUTES (TTL: 24h)
  GET ecampus.ncfu.ru/api/institutes?branch=1,2,3
  → parse → upsert MongoDB institutes

Phase 2 — GROUPS (TTL: 24h)
  Для каждого института:
    GET /api/specialties?institute=X → GET /api/groups?specialty=Y
    → upsert MongoDB groups, teachers, rooms

Phase 3 — SCHEDULES (smart diff-sync)
  Для каждой группы (concurrent, CHUNK_SIZE=10):
    GET /api/schedule?group=X&week=N  (3 недели вперёд)
    →
    new_hash = canonical_hash(data) # исключает volatile-поля: _id, scraped_at
    stored_hash = group.schedule_hash
    ├── SAME   → skip (экономия I/O и записей)
    └── DIFFER →
               bulk_replace в MongoDB
               Redis KEYS DELETE pattern "gql:*"  ← инвалидация кеша
               ScrapeLog.insert(status="ok", ...)
```

### Обработка сбоев

- **tenacity**: retry с exponential backoff для HTTP-запросов к eCampus
- **COOLDOWN_AFTER_FAILURES=3**: после 3 ошибок подряд — пауза 30 секунд
- **ScrapeLog**: каждый запуск записывается в MongoDB (статус, ошибки, время)
- **_refresh_in_progress**: set предотвращает дублирующиеся фоновые обновления

### APScheduler jobs

```python
# Два задания:
1. hourly_scrape:
   - IntervalTrigger(hours=SCRAPE_INTERVAL_HOURS)  # default: 1h
   - + первый запуск через 5 сек после старта приложения

2. daily_cleanup:
   - CronTrigger(hour=CLEANUP_HOUR_UTC, minute=0, timezone="UTC")
   - Удаляет устаревшие activity logs
```

---

## GraphQL схема

### Типы запросов (Query)

```graphql
type Query {
  institutes(q: String): [InstituteType!]!
  
  groups(q: String, instituteName: String, course: Int,
         first: Int = 50, after: String): GroupConnection!
  
  groupSchedule(groupId: Int, groupName: String,
                fromDate: String, toDate: String,
                week: Int): [DayType!]!
  
  teachers(q: String, subject: String, first: Int = 50): TeacherConnection!
  teacherSchedule(teacherId: Int, teacherName: String,
                  fromDate: String, toDate: String): [DayType!]!
  
  rooms(q: String, building: String, first: Int = 50): RoomConnection!
  roomSchedule(roomId: Int, roomName: String,
               fromDate: String, toDate: String): [DayType!]!
  
  freeRooms(at: String, duration: Int = 90,
            building: String): [FreeRoomType!]!
  
  lessonsNow: [JSON!]!
  lessonsOn(date: String!, groupName: String, teacherName: String,
            roomName: String, instituteName: String,
            subject: String, first: Int = 50): LessonConnection!
  
  search(q: String!, instituteId: Int): SearchResult!
  
  overview(recentScrapesLimit: Int = 5): OverviewType!
}

type Mutation {
  triggerScrape(mode: String = "incremental"): ScrapeResultType!
}

type Subscription {
  scheduleUpdated(groupId: Int): ScheduleUpdatedEvent!
}
```

**Защиты:**
- Максимальная глубина вложенности: **5 уровней**
- Максимальный размер документа: **1000 токенов**
- GraphiQL IDE: требует заголовок `X-Admin-Secret`

---

## Инфраструктура и деплой

### Docker Compose порядок старта

```
mongo    → (healthy)
redis    → (healthy)
backend  → depends on: mongo:healthy, redis:healthy
bot      → depends on: mongo:healthy, redis:healthy, backend:healthy
miniapp  → depends on: mongo:healthy, redis:healthy, backend:healthy
nginx    → depends on: all 3 app services (healthy)
```

> [!WARNING]
> Nginx стартует **только после** health-check всех 3 прикладных сервисов. Первый старт занимает 60–90 секунд — это нормально.

### Secrets management

```
/etc/ncfu/secrets  ← root:root, chmod 600, никогда в репозиторий
       │
  setup-secrets.sh  ← интерактивное создание
       │
  deploy.sh          ← source /etc/ncfu/secrets → передаёт в docker compose
       │
  docker-compose.yml ← environment: ${VAR}
       │
  app/core/config.py ← pydantic SecretStr (не в repr, не в логах)
```

**Почему `/etc/ncfu/secrets`, а не `.env`?**
- Переживает `git pull` (файл вне репозитория)
- Переживает перезагрузку сервера
- Только root имеет доступ
- Легко ротировать: редактировать → `make restart`

### Nginx конфигурация — ключевые моменты

```nginx
# Динамическое разрешение имён контейнеров:
resolver 127.0.0.11 valid=5s ipv6=off;
set $upstream_backend http://backend:8000;
# → nginx стартует даже если backend ещё не готов

# Security headers:
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

```

---

## ✅ Чек-лист разработчика

После прочтения этого документа вы должны уметь:

- [ ] Объяснить, какой сервис за что отвечает и где границы ответственности
- [ ] Нарисовать схему прохождения запроса от Telegram до ответа пользователю
- [ ] Понять, почему система использует две MongoDB базы и что в каждой
- [ ] Объяснить 3-фазный scraper и smart diff-sync
- [ ] Описать систему квот: откуда берётся cap, как работает TTL
- [ ] Назвать все уровни безопасности в правильном порядке
- [ ] Понять, как работает GraphQL-кеш и когда он инвалидируется
- [ ] Объяснить, почему секреты хранятся в `/etc/ncfu/secrets`, а не в `.env`
