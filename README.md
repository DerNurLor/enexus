# 🎓 NCFU Schedule Bot

> Умный Telegram-бот расписания СКФУ с AI-обработкой естественного языка, Telegram Mini App и полноценной панелью администратора.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0)](https://aiogram.dev)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248?logo=mongodb)](https://mongodb.com)
[![Redis](https://img.shields.io/badge/Redis-7.4-DC382D?logo=redis)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)

---

## 🚀 Что это такое?

**NCFU Schedule Bot** — система расписания для [Северо-Кавказского федерального университета](https://ncfu.ru). Студент пишет боту на обычном русском языке — *«Где пара через 5 минут у Подзолко?»* или *«Свободные аудитории в корпусе 11 с 14:00»* — и получает точный ответ за секунды.

Система состоит из 4 взаимосвязанных сервисов: API-бэкенда с GraphQL, Telegram-бота с AI, Mini App и панели администратора. Все сервисы объединены через общие MongoDB и Redis, деплоятся одной командой.

---

## ✨ Ключевые возможности

| Возможность | Описание |
|---|---|
| 🤖 **AI-понимание запросов** | OpenAI + Instructor извлекают интент из любого текста на русском |
| 📅 **Актуальное расписание** | Автопарсинг ecampus.ncfu.ru каждый час, смарт-диффсинк |
| 📱 **Telegram Mini App** | Полноценное React SPA прямо внутри Telegram |
| 🚪 **Свободные аудитории** | «Где сейчас можно занять место?» — мгновенный ответ |
| 👥 **Групповые чаты** | Бот работает в группах через @упоминание, не спамит |
| 🔍 **Умный поиск** | Нечёткое совпадение имён, группы в любом формате написания |
| ⚙️ **Панель администратора** | Пользователи, чаты, тикеты, аналитика, Q&A отзывы |
| 🛡️ **RBAC + 2FA + JWT** | Роли, права, TOTP двухфакторная аутентификация |
| 📊 **Квоты и лимиты** | Гибкое управление лимитами — глобально, на чат и на пользователя |

---

## ⚡ Быстрый старт — 5 минут до работающего стека

```bash
# 1. Клонировать
git clone https://github.com/your/ncfu-bot.git /opt/ncfu
cd /opt/ncfu

# 2. Получить секреты (интерактивно — около 2 минут)
sudo bash setup-secrets.sh

# 3. Запустить весь стек
make up

# 4. Проверить что всё поднялось
make health
```

> [!NOTE]
> Перед запуском нужны: токен бота от @BotFather, OpenAI API Key и домен с HTTPS.
> Подробные инструкции — в [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md#первый-деплой).

---

## 🏗 Архитектура — одним взглядом

```
Пользователь → Telegram → HTTPS → Nginx :80
                                       │
                    ┌──────────────────┼─────────────────────┐
                    │                  │                      │
              bot :8001          miniapp :8002         dashboard :8003
           (aiogram 3)          (React SPA)            (Admin Panel)
                    │                  │
                    └────────┬─────────┘
                             │ GraphQL / HTTP
                       backend :8000
                    (REST + GraphQL + Scraper)
                             │
                    ┌────────┴────────┐
               MongoDB :27017    Redis :6379
```

Подробная архитектурная документация с диаграммами — [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 📦 Что входит в систему

| Сервис | Порт | Технологии | Описание |
|---|---|---|---|
| `backend` | 8000 | FastAPI, Strawberry GraphQL, Beanie | REST API + GraphQL + Scraper расписания |
| `bot` | 8001 | aiogram 3, OpenAI, instructor | Telegram-бот с NLU |
| `miniapp` | 8002 | FastAPI + React 18 + Vite + Apollo | Telegram Mini App |
| `dashboard` | 8003 | FastAPI + React (inline) | Панель администратора |
| `mongo` | 27017 | MongoDB 7.0 | Основная база данных |
| `redis` | 6379 | Redis 7.4 | Кеш, квоты, сессии |
| `nginx` | 80 | Nginx 1.27 | Прокси, роутинг, rate limiting |

---

## 🎮 Управление стеком — всё через Make

```bash
# ── Жизненный цикл ──────────────────────────
make up                    # поднять весь стек
make pull                  # git pull + rebuild + restart
make stop                  # остановить
make down                  # остановить и удалить контейнеры
make restart               # перезапустить без пересборки
make fresh                 # ⚠️ полный сброс (УДАЛЯЕТ данные MongoDB)

# ── Обновление отдельного сервиса ────────────
make build bot             # пересобрать только бота
make build backend miniapp # несколько сервисов
make build dashboard       # только дашборд

# ── Мониторинг ───────────────────────────────
make status                # статус контейнеров
make health                # HTTP health-check каждого сервиса
make logs bot              # логи бота (tail -f)
make logs miniapp n=500    # последние 500 строк

# ── Прямой доступ ────────────────────────────
make mongo                 # MongoDB shell
make redis                 # Redis CLI
make shell bot             # bash внутри контейнера
```

---

## 🤖 Бот — примеры запросов

Бот понимает свободный русский текст. Вот что он умеет:

```
📅 Расписание группы:
  "Расписание ИСС-б-о-22-3 на эту неделю"
  "Что у группы АИС25 завтра?"
  "Пары ИСС-22 на следующей неделе"

👤 По преподавателю:
  "Где Подзолко сейчас?"
  "Расписание Иванова И.И. на завтра"
  "Что ведёт Щербина в четверг?"

🚪 По аудитории:
  "Свободные аудитории в корпусе 11"
  "Что сейчас в аудитории 11-405?"
  "Свободные аудитории с 14:00"
  "Когда завтра свободен корпус 3?"

🔍 Поиск:
  "Найди группу ИСС"
  "Найди Петрова"
  "Список институтов"
```

> [!TIP]
> Название группы можно писать в любом формате: `исс б о 22 3`, `ISS-b-o-22-3`, `аис25` — бот всё поймёт.

---

## 📚 Документация

| Документ | Содержание |
|---|---|
| **[Documentation/ARCHITECTURE.md](ARCHITECTURE.md)** | Архитектура, схемы, потоки данных, AI-пайплайн, безопасность |
| **[Documentation/API.md](API.md)** | REST + GraphQL + WebSocket — полный API Reference |
| **[Documentation/USER_GUIDE.md](USER_GUIDE.md)** | Руководство пользователя бота и Mini App |
| **[Documentation/DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** | Локальный запуск, разработка, деплой, CI/CD |
| **[Documentation/CONTRIBUTING.md](CONTRIBUTING.md)** | Как участвовать в разработке |
| **[Documentation/TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | FAQ и решение типичных проблем |
| **[CHANGELOG.md](CHANGELOG.md)** | История изменений |

---

## 🔑 Необходимые сервисы

Перед деплоем нужно получить:

| Что | Где получить | Обязательно |
|---|---|---|
| Telegram Bot Token | [@BotFather](https://t.me/BotFather) → `/newbot` | ✅ |
| OpenAI API Key | [platform.openai.com](https://platform.openai.com/api-keys) | ✅ |
| HTTPS-домен | Любой DNS + Let's Encrypt | ✅ |
| Support Bot Token | [@BotFather](https://t.me/BotFather) → `/newbot` | ➖ |
| Sentry DSN | [sentry.io](https://sentry.io) | ➖ |

---

## 📋 Требования к серверу

- **OS**: Ubuntu 20.04+ / Debian 11+
- **RAM**: от 2 GB (рекомендуется 4 GB)
- **Docker**: ≥ 24.0 + Docker Compose ≥ 2.20
- **Открытые порты**: 80 (Nginx), 443 (если внешний TLS-терминатор)

---

## 🔐 Безопасность

- Секреты хранятся в `/etc/ncfu/secrets` (chmod 600, только root)
- JWT-токены с коротким TTL (60 мин) + refresh (30 дней)
- Telegram webhook верифицируется через `X-Telegram-Bot-Api-Secret-Token`
- GraphQL защищён от DDoS: depth limit (5 уровней), token limit (1000)
- Rate limiting на всех уровнях: nginx, FastAPI middleware, Redis counters
- `pydantic SecretStr` — секреты не попадают в логи и repr

---

## 📄 Лицензия

MIT — см. [LICENSE](LICENSE).

---

## 💬 Поддержка

- Вопросы и баги → `/support <текст>` прямо в боте
- Идеи → `/suggest <текст>`
- Или создайте Issue на GitHub
