# 📡 API Reference

> Полная спецификация REST API, GraphQL API и WebSocket-подписок. Актуально для версии 2.0.

---

## Содержание

- [Базовые URL](#базовые-url)
- [Аутентификация](#аутентификация)
- [REST API — Backend](#rest-api--backend)
- [GraphQL API](#graphql-api)
- [Mini App API](#mini-app-api)
- [Коды ошибок](#коды-ошибок)
- [Примеры запросов](#примеры-запросов)
- [Чек-лист разработчика](#чек-лист-разработчика)

---

## Базовые URL

| Сервис | Внутренний URL | Через Nginx |
|---|---|---|
| backend | `http://backend:8000` | `https://yourdomain.com/` |
| bot | `http://bot:8001` | `https://yourdomain.com/webhook/` |
| miniapp | `http://miniapp:8002` | `https://yourdomain.com/miniapp/` |

> [!NOTE]
> В production все запросы проходят через Nginx на порту 80 (или через внешний TLS-терминатор на 443). Прямые порты `8000–8003` привязаны к `127.0.0.1` и не доступны снаружи.

---

## Аутентификация

### JWT Bearer Token

Большинство защищённых эндпоинтов требуют JWT в заголовке:

```http
Authorization: Bearer <access_token>
```

**Получение токена:**

```http
POST /miniapp/auth
Content-Type: application/json

{
  "init_data": "<Telegram WebApp.initData string>"
}
```

**Ответ:**

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "tg_id": 123456789,
    "first_name": "Иван",
    "roles": ["user"],
    "permissions": [],
    "is_beta": false,
    "is_admin": false
  }
}
```

**Параметры токена:**
- Алгоритм: `HS256`
- Срок жизни: **60 минут**
- При истечении: повторить POST `/miniapp/auth` (SPA делает это автоматически)

### Admin Secret (GraphQL IDE)

```http
X-Admin-Secret: <GRAPHQL_SECRET>
```

Требуется только для доступа к GraphiQL IDE. API-запросы работают без него.

### Telegram Webhook Secret

```http
X-Telegram-Bot-Api-Secret-Token: <TELEGRAM_WEBHOOK_SECRET>
```

Автоматически проставляется Telegram при доставке обновлений. Внешние запросы без этого заголовка получают 403.

---

## REST API — Backend

**Base URL:** `https://yourdomain.com`

### Health

#### `GET /health`

```json
{"status": "ok", "service": "backend", "version": "2.0.0"}
```

### Расписание

#### `GET /api/groups`

Список всех групп.

**Query params:**

| Параметр | Тип | Описание |
|---|---|---|
| `q` | string | Фильтр по названию (подстрока) |
| `institute_id` | int | Фильтр по ID института |
| `course` | int 1–6 | Фильтр по курсу |
| `has_schedule` | bool | Только группы с расписанием |
| `limit` | int (1–500) | Лимит результатов, default 50 |

**Пример ответа:**

```json
{
  "total": 3,
  "groups": [
    {
      "group_id": 1234,
      "name": "ИСС-б-о-22-3",
      "institute_name": "Институт информационных технологий",
      "speciality_name": "Информационные системы и технологии",
      "course": 3,
      "academic_year": "2022",
      "has_schedule": true,
      "days_count": 147,
      "schedule_scraped_at": "2026-03-09T12:00:00"
    }
  ]
}
```

---

#### `GET /api/teachers`

Список преподавателей.

**Query params:** `q`, `subject`, `institute_id`, `has_schedule`, `limit`

```json
{
  "total": 1,
  "teachers": [
    {
      "teacher_id": 567,
      "full_name": "Подзолко Михаил Александрович",
      "short_name": "Подзолко М.А.",
      "institute_names": ["ИИТ"],
      "subjects": ["Алгоритмы", "Структуры данных"],
      "lesson_types": ["Лекция", "Практика"],
      "group_count": 12,
      "has_schedule": true,
      "schedule_scraped_at": "2026-03-09T12:00:00"
    }
  ]
}
```

---

#### `GET /api/rooms`

Список аудиторий.

**Query params:** `q`, `building`, `subject`, `has_schedule`, `limit`

```json
{
  "total": 1,
  "rooms": [
    {
      "room_id": 890,
      "name": "11-405",
      "building": "11",
      "subjects": ["Алгоритмы"],
      "group_count": 8,
      "teacher_count": 4,
      "has_schedule": true
    }
  ]
}
```

---

#### `GET /api/institutes`

Список институтов.

```json
[
  {
    "institute_id": 1,
    "name": "Институт информационных технологий",
    "short_name": "ИИТ",
    "buildings": ["11", "12"]
  }
]
```

---

### Поиск

#### `GET /api/search?q=<query>&limit=20`

Универсальный поиск по группам, преподавателям и аудиториям.

```json
{
  "query": "ИСС",
  "results": {
    "groups": [
      {"group_id": 1234, "name": "ИСС-б-о-22-3",
       "institute_name": "ИИТ", "course": 3}
    ],
    "teachers": [],
    "rooms": []
  },
  "counts": {"groups": 1, "teachers": 0, "rooms": 0}
}
```

---

#### `GET /api/search/now`

Все занятия прямо сейчас.

**Query params:** `entity_type` (group | teacher | room), `institute_id`

```json
{
  "date": "2026-03-09",
  "time": "14:05",
  "total": 42,
  "lessons": [
    {
      "entity_type": "group",
      "entity_id": 1234,
      "entity_name": "ИСС-б-о-22-3",
      "date": "2026-03-09",
      "time_start": "14:00",
      "time_end": "15:30",
      "subject": "Алгоритмы и структуры данных",
      "lesson_type": "Лекция",
      "teacher_name": "Подзолко М.А.",
      "classroom": "11-405"
    }
  ]
}
```

---

#### `GET /api/search/at?dt=2026-03-09T14:00`

Занятия в конкретный момент.

**Query params:** `dt` (ISO datetime, обязательный), `entity_type`, `institute_id`

---

#### `GET /api/search/free-rooms?dt=2026-03-09T14:00&building=11&duration=90`

Свободные аудитории в конкретное время.

| Параметр | Тип | Описание |
|---|---|---|
| `dt` | ISO datetime | Начало интервала (обязательный) |
| `building` | string | Фильтр по корпусу |
| `duration` | int 30–240 | Длительность в минутах, default 90 |

```json
{
  "datetime": "2026-03-09T14:00:00",
  "duration_min": 90,
  "free_count": 12,
  "busy_count": 8,
  "free_rooms": [
    {"room_id": 890, "name": "11-405", "building": "11"}
  ],
  "busy_rooms": [
    {
      "room_id": 891, "name": "11-406", "building": "11",
      "conflicts": [
        {"time_start": "14:00", "time_end": "15:30",
         "subject": "Математика", "group": "МАТ-22"}
      ]
    }
  ]
}
```

---

#### `GET /api/search/next?group_id=1234&count=3`

Следующие N занятий для группы/преподавателя/аудитории.

| Параметр | Тип | Описание |
|---|---|---|
| `teacher_id` / `room_id` / `group_id` | int | Хотя бы один обязателен |
| `count` | int 1–20 | Количество занятий, default 1 |
| `from_dt` | ISO datetime | Начало поиска, default: сейчас |

---

#### `GET /api/search/day?day=2026-03-09`

Все занятия за конкретный день с фильтрацией.

**Query params:** `day` (YYYY-MM-DD, обязательный), `entity_type`, `subject`, `lesson_type`, `teacher_name`, `room_name`

---

#### `GET /api/search/week?week=10&year=2026`

Все занятия за ISO-неделю.

---

#### `GET /api/search/range?from_date=2026-03-01&to_date=2026-03-31`

Занятия в диапазоне дат (максимум 90 дней).

---

#### `GET /api/search/conflicts?from_date=2026-03-09&to_date=2026-03-10&check_type=both`

Конфликты расписания (один преподаватель/аудитория в два места одновременно).

**Query params:** `from_date`, `to_date` (максимум 14 дней), `check_type` (teacher | room | both)

---

#### `GET /api/search/teacher-groups?teacher_id=567`

Группы, у которых ведёт конкретный преподаватель.

**Query params:** `teacher_id` (обязательный), `with_schedule` (bool), `from_date`, `to_date`

---

### Обзор

#### `GET /api/overview`

Общая статистика системы.

```json
{
  "total_groups": 450,
  "total_teachers": 820,
  "total_rooms": 210,
  "total_lessons": 125000,
  "total_institutes": 12,
  "scrape_health": "ok",
  "last_scrape_at": "2026-03-09T13:00:00",
  "recent_scrapes": [...]
}
```

---

### Управление скрапером (требует JWT admin)

#### `POST /api/scrape`

```json
{"mode": "incremental"}
```

**mode:** `incremental` (только изменения) | `full` (полный ресинхрон)

```json
{
  "status": "started",
  "mode": "incremental",
  "job_id": "scrape_20260309_140000"
}
```

---

## GraphQL API

**URL:** `https://yourdomain.com/graphql`
**IDE:** открывается в браузере, требует заголовок `X-Admin-Secret`

### Пример запроса расписания группы

```graphql
query GroupSchedule($groupName: String!, $fromDate: String, $toDate: String) {
  groupSchedule(groupName: $groupName, fromDate: $fromDate, toDate: $toDate) {
    date
    weekday
    weekdayName
    weekNumber
    lessons {
      timeStart
      timeEnd
      subject
      lessonType
      teacherName
      teacherId
      roomName
      building
      subgroup
      weekType
      note
    }
  }
}
```

**Переменные:**

```json
{
  "groupName": "ИСС-б-о-22-3",
  "fromDate": "2026-03-09",
  "toDate": "2026-03-15"
}
```

---

### Пример поиска свободных аудиторий

```graphql
query FreeRooms($at: String, $building: String, $duration: Int) {
  freeRooms(at: $at, building: $building, duration: $duration) {
    roomId
    name
    building
    floor
  }
}
```

```json
{"at": "2026-03-09T14:00:00", "building": "11", "duration": 90}
```

---

### Пример универсального поиска

```graphql
query Search($q: String!) {
  search(q: $q) {
    groups {
      groupId
      name
      instituteName
      course
    }
    teachers {
      teacherId
      fullName
      shortName
    }
    rooms {
      roomId
      name
      building
    }
  }
}
```

---

### Мутация — запуск скрапера

```graphql
mutation TriggerScrape {
  triggerScrape(mode: "incremental") {
    status
    mode
    startedAt
  }
}
```

---

### Подписка — обновления расписания (WebSocket)

```graphql
subscription ScheduleUpdates($groupId: Int) {
  scheduleUpdated(groupId: $groupId) {
    groupId
    groupName
    updatedAt
    changedDates
  }
}
```

**WebSocket URL:** `wss://yourdomain.com/graphql`
**Протокол:** `graphql-ws`

---

### GraphQL ограничения

| Ограничение | Значение | Причина |
|---|---|---|
| Максимальная глубина | 5 уровней | Защита от N+1 атак |
| Максимум токенов | 1000 | Защита от oversized queries |
| Требует авторизацию | IDE только | API открытый |

---

## Mini App API

**Base URL:** `https://yourdomain.com/miniapp`

Все эндпоинты кроме `/miniapp/auth` требуют `Authorization: Bearer <token>`.

### Авторизация

#### `POST /miniapp/auth`

```json
{"init_data": "<Telegram.WebApp.initData>"}
```

**Ответ:** `{token, user}` — см. раздел [Аутентификация](#аутентификация)

---

### Расписание

#### `GET /miniapp/api/schedule`

**Query params:**

| Параметр | Тип | Описание |
|---|---|---|
| `type` | group \| teacher \| room | Тип сущности |
| `id` | string | ID или название |
| `from` | YYYY-MM-DD | Начало диапазона |
| `to` | YYYY-MM-DD | Конец диапазона |
| `week` | int | ISO-номер недели (альтернатива from/to) |

**Ответ:**

```json
{
  "days": [
    {
      "date": "2026-03-09",
      "weekday": 1,
      "weekdayName": "Понедельник",
      "weekNumber": 10,
      "lessons": [
        {
          "timeStart": "08:00",
          "timeEnd": "09:30",
          "subject": "Алгоритмы",
          "lessonType": "Лекция",
          "teacherName": "Подзолко М.А.",
          "roomName": "11-405",
          "building": "11",
          "subgroup": null,
          "weekNumber": 10
        }
      ]
    }
  ],
  "meta": {
    "total": 5,
    "is_beta": false,
    "is_vip": false
  }
}
```

---

#### `GET /miniapp/api/free-rooms`

**Query params:** `at` (ISO datetime, default: сейчас), `duration` (min, default 90), `building`

---

#### `GET /miniapp/api/buildings`

Список корпусов. `[{"building": "11"}, {"building": "12"}, ...]`

---

#### `GET /miniapp/api/search?q=<query>&type=group`

**Query params:** `q` (обязательный), `type` (group | teacher | room | все)

---

### Профиль и лимиты

#### `GET /miniapp/api/profile/limits`

```json
{
  "used": 2,
  "cap": 3,
  "remaining": 1,
  "exhausted": false,
  "ttl_secs": 21600
}
```

---

### Избранное

#### `GET /miniapp/api/favorites`

```json
[
  {"type": "group", "id": "ИСС-б-о-22-3", "label": "ИСС-б-о-22-3"},
  {"type": "teacher", "id": "567", "label": "Подзолко М.А."}
]
```

#### `POST /miniapp/api/favorites`

```json
{"type": "group", "id": "ИСС-б-о-22-3", "label": "ИСС-б-о-22-3"}
```

#### `DELETE /miniapp/api/favorites/{fav_id}`

---

### Настройки

#### `GET /miniapp/api/settings`

```json
{
  "weekFromMonday": true,
  "time24h": true,
  "compact": false,
  "notifications": false,
  "theme": "auto",
  "accent_color": "#7c6eff"
}
```

#### `POST /miniapp/api/settings`

Merge-патч существующих настроек:

```json
{"theme": "dark", "compact": true}
```

---

### Поддержка

#### `POST /miniapp/api/support`

```json
{"message": "Не могу найти расписание группы АИС-25", "category": "question"}
```

**Категории:** `bug` | `question` | `suggestion` | `other`

```json
{
  "ticket_id": "64f1a2b3",
  "status": "open",
  "message": "Обращение принято. Номер: 64f1a2b3"
}
```

---

## Коды ошибок

| HTTP код | Описание |
|---|---|
| `200` | Успех |
| `400` | Неверные параметры запроса |
| `401` | Не авторизован (нет или истёк JWT) |
| `403` | Нет права доступа |
| `404` | Ресурс не найден |
| `422` | Ошибка валидации (FastAPI) |
| `429` | Превышен rate limit |
| `500` | Внутренняя ошибка сервера |

**Формат ошибки (FastAPI standard):**

```json
{
  "detail": "Teacher not found"
}
```

**Формат ошибки валидации:**

```json
{
  "detail": [
    {
      "loc": ["query", "from_date"],
      "msg": "invalid date format",
      "type": "value_error"
    }
  ]
}
```

---

## Примеры запросов

### curl — получить расписание группы

```bash
# GraphQL-запрос через curl
curl -X POST https://yourdomain.com/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ groupSchedule(groupName: \"ИСС-б-о-22-3\", fromDate: \"2026-03-09\", toDate: \"2026-03-15\") { date lessons { timeStart subject teacherName } } }"
  }'
```

### Python — запрос к Mini App API

```python
import httpx

# 1. Авторизация
resp = httpx.post("https://yourdomain.com/miniapp/auth", json={
    "init_data": telegram_init_data  # строка из Telegram.WebApp.initData
})
token = resp.json()["token"]

# 2. Получить расписание
headers = {"Authorization": f"Bearer {token}"}
schedule = httpx.get(
    "https://yourdomain.com/miniapp/api/schedule",
    params={"type": "group", "id": "ИСС-б-о-22-3", "week": 10},
    headers=headers
).json()

for day in schedule["days"]:
    print(f"\n{day['weekdayName']} {day['date']}")
    for lesson in day["lessons"]:
        print(f"  {lesson['timeStart']} {lesson['subject']}")
```

### JavaScript — GraphQL с Apollo Client

```javascript
import { ApolloClient, InMemoryCache, gql } from '@apollo/client';

const client = new ApolloClient({
  uri: 'https://yourdomain.com/graphql',
  cache: new InMemoryCache(),
});

const { data } = await client.query({
  query: gql`
    query FreeRooms($at: String!, $building: String) {
      freeRooms(at: $at, building: $building, duration: 90) {
        roomId name building floor
      }
    }
  `,
  variables: {
    at: new Date().toISOString(),
    building: '11',
  },
});

console.log(`Свободных аудиторий: ${data.freeRooms.length}`);
data.freeRooms.forEach(r => console.log(`  ${r.name} (корпус ${r.building})`));
```

---

## ✅ Чек-лист разработчика

После прочтения этого документа вы должны уметь:

- [ ] Написать GraphQL-запрос для получения расписания группы на неделю
- [ ] Получить список свободных аудиторий через REST API
- [ ] Авторизоваться в Mini App API и получить профиль пользователя
- [ ] Понять разницу между `GET /api/search/now` и GraphQL `lessonsNow`
- [ ] Сформировать запрос для поиска конфликтов расписания за 3 дня
