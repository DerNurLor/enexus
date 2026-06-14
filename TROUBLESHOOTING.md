# 🔧 Troubleshooting & FAQ

> Решения типичных проблем, диагностические команды и ответы на частые вопросы.

---

## Содержание

- [Быстрая диагностика](#быстрая-диагностика)
- [Стек не запускается](#стек-не-запускается)
- [MongoDB проблемы](#mongodb-проблемы)
- [Redis проблемы](#redis-проблемы)
- [Telegram webhook](#telegram-webhook)
- [Бот не отвечает](#бот-не-отвечает)
- [AI-запросы не работают](#ai-запросы-не-работают)
- [Расписание не обновляется](#расписание-не-обновляется)
- [Mini App проблемы](#mini-app-проблемы)
- [Квоты и лимиты](#квоты-и-лимиты)
- [Проблемы с сертификатами SSL](#проблемы-с-сертификатами-ssl)
- [Производительность](#производительность)
- [Мигировать данные](#мигировать-данные)
- [Аварийное восстановление](#аварийное-восстановление)
- [FAQ](#faq)
- [Чек-лист разработчика](#чек-лист-разработчика)

---

## Быстрая диагностика

Прежде чем углубляться в конкретную проблему, выполните эти команды:

```bash
# 1. Статус всех контейнеров
make status

# 2. Health-check всех сервисов
make health

# 3. Логи последних 50 строк всех сервисов
docker compose logs --tail=50

# 4. Ресурсы (CPU/память)
docker stats --no-stream
```

**Ожидаемый результат `make status`:**

```
NAME            STATUS          PORTS
ncfu-nginx      Up 2 hours      0.0.0.0:80->80/tcp
ncfu-backend    Up 2 hours      127.0.0.1:8000->8000/tcp
ncfu-bot        Up 2 hours      127.0.0.1:8001->8001/tcp
ncfu-miniapp    Up 2 hours      127.0.0.1:8002->8002/tcp
ncfu-mongo      Up 2 hours (healthy)
ncfu-redis      Up 2 hours (healthy)
```

Если какой-то контейнер показывает `Exited` или `Restarting` — это проблема.

---

## Стек не запускается

### Симптом: `make up` завершается с ошибкой

```bash
# Посмотреть детали:
docker compose up --no-build 2>&1 | tail -50
```

### Симптом: Контейнер сразу выходит (Exited)

```bash
# Логи упавшего контейнера:
make logs backend
make logs bot
make logs miniapp
```

**Частые причины и решения:**

#### ❌ `pydantic_core._pydantic_core.ValidationError: ... openai_api_key`

```
Причина: OPENAI_API_KEY не задан или пустой
Решение:
  sudo nano /etc/ncfu/secrets
  # Добавить/исправить: OPENAI_API_KEY=sk-proj-...
  make restart
```

#### ❌ `ServerSelectionTimeoutError: ... Authentication failed`

```
Причина: Неверный пароль MongoDB (или спецсимволы в пароле)
Решение: см. раздел "MongoDB проблемы"
```

#### ❌ `WRONGPASS invalid username-password pair`

```
Причина: Неверный пароль Redis
Решение: см. раздел "Redis проблемы"
```

#### ❌ `Port 80 is already in use`

```bash
# Найти что занимает порт:
sudo ss -tlnp | grep :80
sudo lsof -i :80

# Остановить конкурента (например apache2):
sudo systemctl stop apache2
sudo systemctl disable apache2

# Или изменить порт в docker-compose.yml:
ports:
  - "8080:80"  # вместо 80:80
```

#### ❌ Nginx стартует, но другие сервисы нет

```bash
# Nginx ждёт health-check всех 4 сервисов.
# Проверьте каждый сервис по-отдельности:
docker compose up backend -d
docker compose logs backend

# Если backend не стартует — проблема в нём.
# Nginx не причём.
```

---

## MongoDB проблемы

### ❌ Authentication failed / ServerSelectionTimeoutError

**Самая частая причина** — спецсимволы в пароле (`@`, `!`, `#`, `/` и т.д.) ломают MongoDB URI.

```bash
# 1. Проверить текущий пароль:
sudo grep MONGO_PASSWORD /etc/ncfu/secrets

# 2. Если есть спецсимволы — сгенерировать новый безопасный пароль:
LC_ALL=C tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 32
# Пример безопасного: "Kj8mNpQ3wXvR7tYzAb2cDf5e"

# 3. Обновить в секретах:
sudo nano /etc/ncfu/secrets
# Изменить MONGO_PASSWORD на новое значение

# 4. Сбросить БД (пользователь пересоздастся):
make fresh   # ⚠️ УДАЛЯЕТ ВСЕ ДАННЫЕ
# или только удалить volume и пересоздать пользователя:
docker compose down
docker volume rm ncfu_mongo_data
make up
```

> [!WARNING]
> `make fresh` удаляет **все данные** MongoDB, включая пользователей и расписание. Используйте только если данные не критичны или есть бекап.

### ❌ Медленные запросы / таймауты

```bash
# Войти в MongoDB:
make mongo

# Посмотреть медленные операции (>100ms):
use admin
db.currentOp({"secs_running": {$gte: 0}})

# Проверить индексы коллекции lessons:
use ncfu_schedule
db.lessons.getIndexes()

# Если индексов нет — создать (займёт несколько минут):
db.lessons.createIndex({date: 1, group_id: 1})
db.lessons.createIndex({date: 1, teacher_id: 1})
db.lessons.createIndex({date: 1, room_id: 1})
db.lessons.createIndex({date: 1, time_start: 1})
```

### ❌ Disk full — MongoDB не пишет

```bash
# Проверить место:
df -h

# Найти большие файлы:
du -sh /var/lib/docker/volumes/ncfu_mongo_data

# Почистить старые логи MongoDB:
make mongo
use admin
db.runCommand({logRotate: 1})

# Компактизировать коллекцию (освобождает место):
use ncfu_schedule
db.runCommand({compact: "lessons"})
```

---

## Redis проблемы

### ❌ WRONGPASS / Connection refused

```bash
# Проверить пароль:
sudo grep REDIS_PASSWORD /etc/ncfu/secrets

# Тест соединения:
docker compose exec redis redis-cli -a "YOUR_REDIS_PASSWORD" PING
# Ожидаемо: PONG

# Если пароль содержит спецсимволы — заменить на безопасный (только a-zA-Z0-9):
sudo nano /etc/ncfu/secrets
make restart
```

### ❌ Redis memory full (OOM)

```bash
make redis

# Проверить использование памяти:
INFO memory
# Смотреть: used_memory_human

# Посмотреть самые большие ключи:
redis-cli --bigkeys

# Очистить просроченшие ключи принудительно:
DEBUG SLEEP 0
BGSAVE

# Если критично — очистить кеш расписания (данные восстановятся сами):
KEYS gql:* | xargs DEL
```

---

## Telegram webhook

### ❌ Бот молчит — webhook не доставляется

**Шаг 1 — Проверить webhook info:**

```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | python3 -m json.tool
```

**Нормальный ответ:**
```json
{
  "url": "https://your-domain.com/webhook/telegram",
  "has_custom_certificate": false,
  "pending_update_count": 0,
  "last_error_date": null,
  "last_error_message": "",
  "max_connections": 40
}
```

**Признаки проблемы:**
- `last_error_message` не пустой
- `pending_update_count` растёт
- `url` неверный или пустой

**Шаг 2 — Частые ошибки:**

| Ошибка | Причина | Решение |
|---|---|---|
| `Connection refused` | Nginx не отвечает | `make status`, проверить порт |
| `SSL certificate problem` | Невалидный сертификат | Обновить cert: `certbot renew` |
| `Wrong response from the webhook` | Сервис вернул не 200 | `make logs bot n=50` |
| `PEER_CERT_UNTRUSTED` | Self-signed cert | Telegram требует публичный CA |
| `Forbidden` | Неверный secret_token | Переустановить webhook |

**Шаг 3 — Переустановить webhook:**

```bash
# Отменить текущий:
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"

# Установить заново:
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/webhook/telegram",
    "secret_token": "'$(sudo grep TELEGRAM_WEBHOOK_SECRET /etc/ncfu/secrets | cut -d= -f2)'"
  }'
```

### ❌ Бот отвечает, но с большой задержкой

```bash
# Проверить pending updates:
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | python3 -c "import sys,json; d=json.load(sys.stdin)['result']; print(f'Pending: {d[\"pending_update_count\"]}')"

# Если много (>100) — бот не успевает обрабатывать
# Проверить: не завис ли handler
make logs bot n=100 | grep -E "ERROR|WARNING|timeout"

# Перезапустить бот:
docker compose restart bot
```

---

## Бот не отвечает

### ❌ Команды работают, но текстовые запросы нет

```bash
# Скорее всего проблема с OpenAI API:
make logs bot n=50 | grep -i "openai\|instructor\|error"
```

Частые причины:
- Исчерпан OpenAI credit balance
- API ключ истёк или отозван
- Таймаут OpenAI (редко)

```bash
# Проверить ключ:
curl -s https://api.openai.com/v1/models \
  -H "Authorization: Bearer $(sudo grep OPENAI_API_KEY /etc/ncfu/secrets | cut -d= -f2)" \
  | python3 -m json.tool | head -20
# Ожидаемо: список моделей. Если 401 — ключ неверный.
```

### ❌ Бот отвечает «❌ Ошибка при загрузке расписания» + ERR-ID

```bash
# Найти ошибку по ERR-ID в MongoDB:
make mongo
use ncfu_auth
db.auth_error_logs.findOne({error_id: "ERR-ABCDEF"})

# Или в логах:
make logs bot n=200 | grep "ERR-ABCDEF"
```

### ❌ Бот не реагирует в группе

В групповом чате бот отвечает только на прямые обращения:
- `@bot_username ваш запрос`
- Reply на сообщение бота
- Команды (`/help`, `/start` и т.д.)

Убедитесь, что бот не удалён из группы и имеет права на отправку сообщений.

---

## AI-запросы не работают

### ❌ `RateLimitError` / `InsufficientQuotaError` от OpenAI

```bash
make logs bot n=50 | grep -i "openai\|ratelimit\|quota"
```

Решение:
1. Проверьте баланс на [platform.openai.com/usage](https://platform.openai.com/usage)
2. Если баланс исчерпан — пополните или используйте другой ключ
3. Временно можно снизить нагрузку: увеличить TTL кеша в `.env`

```bash
# Временное увеличение TTL кеша (уменьшает число запросов к OpenAI):
# В /etc/ncfu/secrets или .env:
CACHE_TTL_NOW=120   # было 60
CACHE_TTL_DAY=1200  # было 600
make restart
```

### ❌ Неправильно распознаётся интент

Если бот часто неправильно понимает запросы — проблема в system prompt или в очень необычном формате запроса.

```bash
# Включить DEBUG логирование для ai_handler:
make logs bot n=100 | grep -i "intent\|dispatch"

# Посмотреть что именно распознал AI:
# (ищем строку "Intent extracted:")
make logs bot n=200 | grep "Intent"
```

Если проблема системная — создайте Issue с примерами запросов.

---

## Расписание не обновляется

### ❌ Расписание устарело / не обновлялось

```bash
# Посмотреть последние запуски скрапера:
make mongo
use ncfu_schedule
db.scrape_logs.find().sort({started_at: -1}).limit(5).pretty()

# Принудительно запустить скрапер:
curl -X POST http://localhost:8000/api/scrape \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"mode": "incremental"}'

# Или через GraphQL:
# POST /graphql с запросом: mutation { triggerScrape(mode: "incremental") { status } }
```

> [!TIP]
> JWT для admin-запросов можно получить через `/miniapp/auth` с admin-аккаунтом, или создать временный через `make shell backend` → Python REPL → `create_access_token(...)`.

### ❌ Скрапер падает с ошибкой

```bash
make logs backend n=100 | grep -i "scraper\|ncfu\|error\|timeout"
```

**Частые причины:**

| Ошибка | Причина | Решение |
|---|---|---|
| `ConnectionTimeout` | ecampus.ncfu.ru недоступен | Подождать, повторить позже |
| `401 Unauthorized` | Сессия к eCampus истекла | [предположение] Обновить куки скрапера |
| `JSONDecodeError` | Изменился формат ответа API | Обновить parser.py |
| `RetryError` | 3+ неудачных попытки подряд | Проверить сеть сервера |

```bash
# Проверить доступность eCampus с сервера:
docker compose exec backend curl -s -o /dev/null -w "%{http_code}" https://ecampus.ncfu.ru
# Ожидаемо: 200 или 302
```

### ❌ Расписание есть в MongoDB, но кеш показывает старое

```bash
# Очистить GraphQL кеш принудительно:
make redis
KEYS gql:* | wc -l    # сколько ключей
KEYS gql:* | xargs DEL
# После этого следующие запросы получат свежие данные из MongoDB
```

---

## Mini App проблемы

### ❌ Mini App не открывается / белый экран

```bash
# 1. Проверить сервис:
curl -s http://localhost:8002/miniapp -o /dev/null -w "%{http_code}"
# Ожидаемо: 200

# 2. Проверить что статика собрана:
ls miniapp/app/miniapp/static/
# Должны быть: index.html, assets/

# 3. Проверить логи:
make logs miniapp n=50
```

**Если нет статики** — нужно пересобрать React SPA:
```bash
cd miniapp/react-src
npm install && npm run build
cp -r dist/* ../app/miniapp/static/
make build miniapp
```

### ❌ `401 Unauthorized` при открытии Mini App

Telegram Mini App требует передачи `initData` при авторизации. Это работает только внутри Telegram — не в обычном браузере.

```bash
# Для разработки — эмулировать initData:
# В React SPA выставить VITE_DEV_MODE=true (предположение / требует уточнения)
```

### ❌ Лимиты показывают неверное значение

```bash
# Проверить текущее значение квоты в Redis:
make redis
GET quota:123456789   # где 123456789 — Telegram ID пользователя

# Проверить AuthUser в MongoDB:
make mongo
use ncfu_auth
db.auth_users.findOne({tg_id: 123456789}, {daily_requests: 1, roles: 1})
```

---

---

## Квоты и лимиты

### ❌ Сбросить лимит пользователя

```bash
# Через Redis CLI:
make redis
DEL quota:123456789   # заменить на реальный tg_id

# Через Python внутри контейнера:
make shell bot
python3 -c "
import asyncio
from app.bot.middlewares.anti_flood import reset_user_quota
asyncio.run(reset_user_quota(123456789))
print('Quota reset!')
"
```

### ❌ Увеличить лимит конкретному пользователю

```bash
make mongo
use ncfu_auth

# Установить персональный лимит 20 запросов:
db.auth_users.updateOne(
  {tg_id: 123456789},
  {$set: {daily_requests: 20}}
)
```

### ❌ Увеличить лимит для конкретного чата

```bash
make mongo
use ncfu_auth   # или ncfu_schedule, в зависимости от коллекции

db.chat_settings.updateOne(
  {chat_id: -1001234567890},   # ID группового чата (отрицательный для супергрупп)
  {$set: {bot_quota_cap: 10, bot_quota_ttl_hours: 7}},
  {upsert: true}
)
```

---

## Проблемы с сертификатами SSL

### ❌ Telegram не доставляет webhook — SSL error

Telegram требует:
- Публичный SSL-сертификат от доверенного CA (не self-signed)
- TLS 1.2+
- Порт 443, 80, 88 или 8443

```bash
# Проверить сертификат:
echo | openssl s_client -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates

# Если истёк — обновить:
sudo certbot renew --force-renewal
sudo systemctl reload nginx  # или caddy

# Проверить цепочку сертификатов:
curl -v https://your-domain.com/health 2>&1 | grep -E "SSL|certificate|verify"
```

### ❌ Certbot не может обновить сертификат

```bash
# Режим standalone (если nginx занимает порт 80):
sudo systemctl stop nginx
sudo certbot certonly --standalone -d your-domain.com
sudo systemctl start nginx

# Или webroot:
sudo certbot renew --webroot -w /var/www/html
```

---

## Производительность

### ❌ Медленные ответы бота (>5 сек)

```bash
# 1. Проверить время ответа OpenAI:
make logs bot n=50 | grep -i "openai\|elapsed\|ms"

# 2. Проверить GraphQL время запроса:
make logs backend n=50 | grep -i "graphql\|elapsed\|slow"

# 3. Посмотреть Redis hit rate:
make redis
INFO stats | grep keyspace_hits
# Высокий hit rate (>80%) = кеш работает хорошо

# 4. MongoDB медленные запросы:
make mongo
use ncfu_schedule
db.setProfilingLevel(1, {slowms: 100})
# После нескольких запросов:
db.system.profile.find().sort({ts: -1}).limit(5).pretty()
```

### ❌ Высокое потребление памяти

```bash
docker stats --no-stream

# Типичное потребление:
# backend:   200–400 MB
# bot:       150–300 MB
# miniapp:   100–200 MB
# mongo:     500 MB – 2 GB
# redis:     50–200 MB
```

Если `bot` или `backend` превышают 1 GB — скорее всего утечка памяти. Перезапуск:

```bash
docker compose restart bot
```

---

## Мигировать данные

### Запустить скрипт миграции

```bash
# Скрипты в backend/app/scripts/:
docker compose exec backend python -m app.scripts.migrate_conversation
docker compose exec backend python -m app.scripts.migrate_null_chat_id
```

### Экспорт/импорт MongoDB

```bash
# Экспорт (бекап):
docker compose exec mongo mongodump \
  --authenticationDatabase admin \
  -u $MONGO_USER -p $MONGO_PASSWORD \
  --db ncfu_schedule \
  --out /tmp/backup

docker cp ncfu-mongo:/tmp/backup ./backup_$(date +%Y%m%d)

# Импорт (восстановление):
docker cp ./backup ncfu-mongo:/tmp/backup
docker compose exec mongo mongorestore \
  --authenticationDatabase admin \
  -u $MONGO_USER -p $MONGO_PASSWORD \
  /tmp/backup
```

---

## Аварийное восстановление

### Сервис постоянно падает и перезапускается

```bash
# Остановить перезапуски, изучить ошибку:
docker compose stop backend
docker compose run --rm backend python -c "from app.main import create_app; print('OK')"
# Если здесь ошибка — смотреть трассировку
```

### Полный сброс (последнее средство)

> [!WARNING]
> Команда ниже **безвозвратно удаляет все данные MongoDB**. Выполняйте только если данные не важны или есть бекап.

```bash
make fresh
# = docker compose down -v && make up

# После: скрапер автоматически запустится через 5 сек и начнёт загрузку данных
```

### Rollback к предыдущей версии

```bash
# Откатить к конкретному коммиту:
git log --oneline -10   # найти нужный commit hash
git checkout <commit_hash>
make pull   # пересобрать
```

---

## FAQ

### ❓ Почему у пользователя только 3 запроса в день?

Это глобальный дефолт (`quota_private=3` в `config.py`). Можно увеличить:

1. **Индивидуально** — в MongoDB `auth_users.daily_requests` для конкретного пользователя
2. **Глобально** — в `/etc/ncfu/secrets` добавить `QUOTA_PRIVATE=10`, затем `make restart`
3. **На чат** — в MongoDB `chat_settings.bot_quota_cap`

### ❓ Можно ли использовать бот без OpenAI?

Нет. AI-обработка (OpenAI + Instructor) — ключевой компонент. Без него бот не сможет понимать свободный текст. Без `OPENAI_API_KEY` бот не запустится.

### ❓ Как часто скрапер обновляет расписание?

По умолчанию каждый час. Можно изменить переменной `SCRAPE_INTERVAL_HOURS` в секретах. После изменения: `make restart`.

### ❓ Данные расписания хранятся или запрашиваются каждый раз?

Хранятся в MongoDB. Скрапер работает по расписанию и обновляет данные. Ответы кешируются в Redis (TTL 60–900 сек в зависимости от типа запроса).

### ❓ Как узнать Telegram ID группы для настройки квоты?

Способы:
1. Переслать сообщение из группы боту [@userinfobot](https://t.me/userinfobot)
2. `make mongo` → `db.chat_settings.find({chat_type: "supergroup"}).limit(5)`

### ❓ Можно ли деплоить без `make fresh` при смене пароля MongoDB?

Нет. MongoDB хранит пользователя с хешированным паролем внутри volume. Если вы меняете `MONGO_PASSWORD`, нужно:

```bash
# Вариант 1 — пересоздать пользователя (без потери данных):
make mongo
use admin
db.changeUserPassword("ncfu_app", "new_password")
# Затем обновить MONGO_PASSWORD и make restart

# Вариант 2 — полный сброс (теряете данные):
make fresh
```

### ❓ Где хранятся загруженные аватары пользователей?

В Docker volume, смонтированном в `/app/static/avatars` внутри контейнера. На хосте это:

```bash
docker volume inspect ncfu_static_data
# Путь: /var/lib/docker/volumes/ncfu_static_data/_data
```

### ❓ Почему бот не отвечает на команды в супергруппе без @упоминания?

Это намеренное поведение — защита от случайного ответа на сообщения других участников. Команды (`/help`, `/start` и т.д.) работают без упоминания, потому что они явно адресованы боту. Обычный текст требует `@bot_username`.

---

## ✅ Чек-лист разработчика

После прочтения этого документа вы должны уметь:

- [ ] Диагностировать проблему за 2 минуты с помощью `make status` + `make logs`
- [ ] Исправить ошибку аутентификации MongoDB/Redis (спецсимволы в пароле)
- [ ] Переустановить Telegram webhook
- [ ] Найти конкретную ошибку по ERR-ID в логах и MongoDB
- [ ] Сбросить квоту пользователя через Redis CLI
- [ ] Принудительно запустить скрапер расписания
- [ ] Очистить GraphQL-кеш при устаревших данных
- [ ] Настроить персональный лимит запросов для пользователя
- [ ] Выполнить аварийный rollback к предыдущей версии
