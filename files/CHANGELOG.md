# 📋 Changelog

Все значимые изменения в проекте документируются здесь.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).  
Проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

---

## [Unreleased]

> Изменения, которые войдут в следующий релиз.

### Added
- _(пока пусто)_

---

## [2.1.0] — 2026-03-09

### Added
- **bot**: Команда `/suggest` — подача предложений/идей. Создаёт тикет с `category=suggestion`, уведомляет администратора
- **bot**: Команда `/about` — информация о боте v2.0, ссылки на Mini App и личный кабинет
- **bot**: Команда `/roles` — отображение ролей со значками (🔴admin 🟠mod 🟡vip 🔵beta ⚪user), персональный лимит
- **dashboard**: Поиск по тексту и ERR-ID в списке отзывов (`GET /feedback?search=`)
- **dashboard**: Навигация между ошибкой и отзывами — кнопка «Найти отзывы с этой ошибкой» и «Перейти к ошибке ERR-XXXXXX»
- **dashboard2**: Компонент `FeedbackQAList` — вкладка `📋 Q&A Список` для анализа пар вопрос/ответ

### Fixed
- **miniapp**: Квота Mini App всегда показывала значение по умолчанию (3) вместо персонального лимита пользователя. Теперь `quota_service.py` корректно читает `AuthUser.daily_requests` из MongoDB

### Changed
- **bot**: Команда `/roles` переписана — добавлено отображение привилегий (`admin:full`, `beta_access`, `floorplan:edit`) и ссылок на панель управления

---

## [2.0.0] — 2026-02-01

> **Breaking Change:** Монолитное приложение разделено на 4 независимых сервиса.

### Added
- **architecture**: Микросервисная декомпозиция — `backend`, `bot`, `miniapp`, `dashboard` как отдельные Docker-контейнеры
- **backend**: Strawberry GraphQL API с depth limiting (max 5) и token limiting (max 1000)
- **backend**: GraphQL Subscription `scheduleUpdated` через WebSocket (`graphql-ws`)
- **backend**: REST `/api/search/*` — 14 эндпоинтов: `now`, `at`, `day`, `week`, `range`, `next`, `free-rooms`, `conflicts`, `teacher-groups` и другие
- **bot**: AI-обработка запросов через OpenAI + Instructor, 12 типов интентов
- **bot**: Пагинация расписания с навигацией ◀/▶ по дням
- **bot**: Кнопки отзыва 👍/👎 на каждый ответ, сохранение в `bot_feedback`
- **bot**: `AntiFloodMiddleware` — защита от флуда (5 msg/min, 2× для Premium)
- **bot**: `MessageLimitMiddleware` — квоты AI-запросов (3/7h private, 3–5/7h group)
- **bot**: Нормализатор названий групп — поддержка латиницы, произвольных пробелов, коротких форм (`аис25` → `аис-б-о-25`)
- **bot**: Disambiguation — кнопки выбора при нескольких совпадениях, пагинация списка
- **miniapp**: Telegram Mini App на React 18 + TypeScript + Vite + Apollo Client
- **miniapp**: Вкладки: Расписание, Свободные аудитории, Избранное, Профиль
- **miniapp**: Автоматическая повторная авторизация при истечении JWT
- **security**: HMAC-SHA256 валидация Telegram initData в Mini App
- **security**: Webhook верификация через `X-Telegram-Bot-Api-Secret-Token`
- **security**: JWT DPoP binding (RFC 9449) для refresh-токенов
- **security**: TOTP 2FA для администраторов
- **infra**: `setup-secrets.sh` — интерактивная настройка секретов с автогенерацией паролей
- **infra**: `deploy.sh` — единая точка деплоя с командами `up`, `pull`, `build`, `restart`, `logs`, `status`, `fresh`
- **infra**: `Makefile` — алиасы для всех операций деплоя
- **observability**: Sentry SDK, OpenTelemetry, Prometheus метрики
- **observability**: ERR-ID система — уникальные коды ошибок для трассировки

### Changed
- **backend**: Перешли с синхронного MongoDB-драйвера на Motor (async) + Beanie ODM
- **backend**: Кеш-стратегия переработана — раздельные TTL для разных типов данных
- **scraper**: 3-фазный пайплайн вместо монолитного парсера; smart diff-sync на основе MD5-хешей
- **auth**: Двойная БД — `ncfu_schedule` и `ncfu_auth` разделены

### Removed
- **bot**: `/mykey` команда отключена (API ключи временно недоступны)
- **backend**: Синхронный `pymongo` заменён на `motor`
- **infra**: Удалены устаревшие `docker-compose.dev.yml` в поддиректориях

### Security
- Все секреты переведены на `pydantic.SecretStr` — не попадают в repr и логи
- CORS-whitelist вместо wildcard `*`
- HTTPS enforce middleware в production
- Rate limiting на всех уровнях: Nginx + FastAPI + Redis counters

---

## [1.5.2] — 2025-12-15

### Fixed
- **bot**: Исправлена ошибка парсинга расписания при отсутствии преподавателя в паре
- **bot**: Команда `/limit` иногда показывала отрицательное значение остатка

### Security
- **deps**: Обновлён `cryptography` до 42.0.8 (CVE-2024-26130)

---

## [1.5.1] — 2025-11-28

### Fixed
- **scraper**: Исправлен краш при парсинге пустых недель у новых групп
- **backend**: `/api/search/conflicts` неверно находил конфликты при парах длиннее 90 минут

### Changed
- **scraper**: `CHUNK_SIZE` увеличен с 5 до 10 для ускорения полной синхронизации

---

## [1.5.0] — 2025-11-10

### Added
- **bot**: Поддержка расписания в групповых чатах — ответ только на @упоминания и reply
- **bot**: При добавлении бота в группу — автоматическое приветственное сообщение
- **bot**: Сохранение всех медиа-сообщений (фото, видео, голос, стикеры) в `chat_messages`
- **backend**: `GET /api/search/teacher-groups` — группы конкретного преподавателя с расписанием
- **dashboard**: Просмотр истории переписки с каждым пользователем

### Fixed
- **bot**: Отредактированные сообщения теперь обновляют запись в MongoDB вместо создания дубля
- **miniapp**: Тема Mini App некорректно определялась в Telegram Desktop на Windows

---

## [1.4.0] — 2025-10-01

### Added
- **bot**: Интент `BuildingScheduleIntent` — «Когда завтра свободен корпус 3?»
- **bot**: Пагинация для длинных результатов поиска при disambiguation
- **backend**: Полнотекстовый поиск по `subject`, `teacher_name`, `room_name` через MongoDB text index

### Changed
- **bot**: Нормализатор групп переписан — теперь обрабатывает транслитерацию через `transliterate` lib
- **scraper**: Retry-логика переведена на `tenacity` с exponential backoff

### Fixed
- **bot**: При ошибке OpenAI API счётчик квоты теперь корректно откатывается (DECR)

---

## [1.0.0] — 2025-09-01

> Первый публичный релиз.

### Added
- Базовый Telegram-бот на aiogram 3
- Парсинг расписания с ecampus.ncfu.ru
- Команды `/start`, `/help`, `/miniapp`, `/support`, `/limit`
- REST API: groups, teachers, rooms, institutes, schedules
- MongoDB + Redis инфраструктура
- Docker Compose деплой
- Nginx reverse proxy

---

## Формат версий

- **Major (X.0.0)** — несовместимые изменения API или архитектуры
- **Minor (0.X.0)** — новые функции, обратно совместимые
- **Patch (0.0.X)** — исправления ошибок, обратно совместимые

## Ссылки

- [Unreleased]: https://github.com/your/ncfu-bot/compare/v2.1.0...HEAD
- [2.1.0]: https://github.com/your/ncfu-bot/compare/v2.0.0...v2.1.0
- [2.0.0]: https://github.com/your/ncfu-bot/compare/v1.5.2...v2.0.0
- [1.5.2]: https://github.com/your/ncfu-bot/compare/v1.5.1...v1.5.2
- [1.5.1]: https://github.com/your/ncfu-bot/compare/v1.5.0...v1.5.1
- [1.5.0]: https://github.com/your/ncfu-bot/compare/v1.4.0...v1.5.0
- [1.4.0]: https://github.com/your/ncfu-bot/compare/v1.0.0...v1.4.0
- [1.0.0]: https://github.com/your/ncfu-bot/releases/tag/v1.0.0
