# 🤝 Contributing Guide

> Руководство для тех, кто хочет улучшить NCFU Schedule Bot. Здесь описано всё: от настройки окружения до отправки pull request.

---

## Содержание

- [Кодекс поведения](#кодекс-поведения)
- [С чего начать](#с-чего-начать)
- [Как сообщить об ошибке](#как-сообщить-об-ошибке)
- [Как предложить улучшение](#как-предложить-улучшение)
- [Настройка окружения разработчика](#настройка-окружения-разработчика)
- [Рабочий процесс разработки](#рабочий-процесс-разработки)
- [Стандарты кода](#стандарты-кода)
- [Структура commit-сообщений](#структура-commit-сообщений)
- [Процесс Pull Request](#процесс-pull-request)
- [Тестирование](#тестирование)
- [Документация](#документация)
- [Чек-лист перед отправкой PR](#чек-лист-перед-отправкой-pr)

---

## Кодекс поведения

Мы стремимся к открытому и доброжелательному сообществу. Участвуя в этом проекте, вы соглашаетесь:

- Уважать других участников вне зависимости от опыта и взглядов
- Принимать конструктивную критику
- Фокусироваться на том, что лучше для проекта и его пользователей
- Не допускать оскорблений, преследований или дискриминации

---

## С чего начать

### Хочу помочь, но не знаю с чего начать

Отличные точки входа для новых контрибьюторов:

1. **Исправить опечатку или улучшить документацию** — самый лёгкий способ начать
2. **Закрыть issue с меткой `good first issue`** — специально отобранные небольшие задачи
3. **Улучшить обработку ошибок** — посмотрите issues с меткой `bug`
4. **Добавить тесты** — покрытие всегда можно улучшить

### Виды вклада

| Тип | Описание |
|---|---|
| 🐛 **Bagfix** | Исправление ошибок |
| ✨ **Feature** | Новая функциональность |
| 📝 **Docs** | Улучшение документации |
| ♻️ **Refactor** | Рефакторинг без изменения поведения |
| ⚡ **Perf** | Улучшение производительности |
| 🧪 **Test** | Добавление или исправление тестов |
| 🔧 **Chore** | Обновление зависимостей, конфигурации |

---

## Как сообщить об ошибке

Перед созданием issue проверьте, что похожего ещё нет в [списке issues](https://github.com/your/ncfu-bot/issues).

### Шаблон баг-репорта

```markdown
**Описание ошибки**
Краткое описание того, что происходит.

**Шаги для воспроизведения**
1. Отправить боту сообщение '...'
2. Нажать кнопку '...'
3. Наблюдать ошибку

**Ожидаемое поведение**
Что должно было произойти.

**Фактическое поведение**
Что происходит вместо этого. Приложите ERR-ID если бот его выдал.

**Окружение**
- Версия: [commit hash или дата]
- OS сервера: Ubuntu 22.04
- Docker: 24.x

**Логи**
```
make logs bot n=50
```
```

> [!TIP]
> Если бот выдал код `ERR-XXXXXX` — обязательно укажите его в репорте. По нему можно мгновенно найти конкретную ошибку в логах.

---

## Как предложить улучшение

Перед тем как писать код для новой функции — создайте issue и опишите идею. Это поможет:

- Убедиться, что функция вписывается в архитектуру
- Получить обратную связь до написания кода
- Избежать дублирования уже начатой работы

### Шаблон предложения функции

```markdown
**Проблема / зачем нужно**
Что сейчас неудобно или чего не хватает.

**Предлагаемое решение**
Как именно это должно работать.

**Альтернативы**
Какие другие решения рассматривались и почему отброшены.

**Затронутые компоненты**
bot / backend / miniapp / all
```

---

## Настройка окружения разработчика

### 1. Форк и клонирование

```bash
# Форкнуть репозиторий через GitHub UI, затем:
git clone https://github.com/YOUR_USERNAME/ncfu-bot.git
cd ncfu-bot

# Добавить upstream для синхронизации:
git remote add upstream https://github.com/original/ncfu-bot.git
```

### 2. Создать ветку для работы

```bash
# Никогда не работайте прямо в main!
git checkout -b feat/exam-schedule
# или
git checkout -b fix/quota-counter-bug
# или
git checkout -b docs/improve-api-reference
```

### 3. Настроить Python-окружение (для разработки без Docker)

```bash
# Создать виртуальное окружение для нужного сервиса:
cd ecampus_bot
python3.11 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install ruff mypy pytest pytest-asyncio  # dev-инструменты
```

### 4. Pre-commit hooks (рекомендуется)

```bash
pip install pre-commit
pre-commit install

# Теперь при каждом git commit автоматически запускается:
# ruff check . && ruff format --check .
```

---

## Рабочий процесс разработки

```
main (stable)
  │
  ├── feat/your-feature     ← ваша ветка
  │     │
  │     ├── коммит 1
  │     ├── коммит 2
  │     └── коммит 3
  │
  └── ← Pull Request → Code Review → Merge
```

### Синхронизация с upstream

Перед началом работы и перед отправкой PR синхронизируйтесь:

```bash
git fetch upstream
git rebase upstream/main
# или
git merge upstream/main
```

---

## Стандарты кода

### Python

Проект использует **ruff** для линтинга и форматирования:

```bash
# Проверить:
ruff check .

# Форматировать:
ruff format .

# Проверить типы:
mypy app/
```

**Ключевые правила:**

- Строки до 120 символов
- Аннотации типов обязательны для публичных функций
- `from __future__ import annotations` в начале каждого файла
- Docstring для всех публичных функций и классов
- `logger.info/warning/error` — не `print()`

**Правильно:**

```python
async def get_schedule(
    group_name: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> List[DayType]:
    """
    Fetch schedule for a group from GraphQL backend.

    Args:
        group_name: Group identifier, e.g. 'ИСС-б-о-22-3'
        from_date: ISO date string YYYY-MM-DD (default: current week start)
        to_date: ISO date string YYYY-MM-DD (default: current week end)

    Returns:
        List of DayType objects with lessons

    Raises:
        httpx.HTTPError: If backend is unreachable
    """
    data = await _gql(_GQL_GROUP_SCHEDULE, {
        "gn": group_name,
        "from": from_date,
        "to": to_date,
    })
    return data.get("groupSchedule", [])
```

**Неправильно:**

```python
async def get_schedule(group_name, from_date=None, to_date=None):
    data = await _gql(_GQL_GROUP_SCHEDULE, {"gn": group_name, "from": from_date, "to": to_date})
    return data.get("groupSchedule", [])
```

### TypeScript (React SPA)

```bash
cd miniapp/react-src
npm run lint    # ESLint
npm run build   # TypeScript compile check
```

**Правила:**

- Строгие TypeScript типы — никаких `any` без явной причины
- Функциональные компоненты + hooks, не классы
- Именованные экспорты предпочтительнее дефолтных (кроме страниц)

### Безопасность кода

> [!WARNING]
> Особое внимание при работе с этими паттернами:

1. **Секреты** — никогда не хардкодьте токены, пароли, ключи. Всё через `settings.*`
2. **Пользовательский ввод** — валидируйте через Pydantic, не доверяйте напрямую
3. **MongoDB** — используйте параметризованные запросы (Beanie ODM), не строковую конкатенацию
4. **Логирование** — не логируйте `SecretStr` поля, не пишите `tg_init_data` в логи

---

## Структура commit-сообщений

Проект следует [Conventional Commits](https://www.conventionalcommits.org/).

### Формат

```
<тип>(<область>): <краткое описание>

[необязательное тело]

[необязательные сноски]
```

### Типы

| Тип | Когда использовать |
|---|---|
| `feat` | Новая функциональность |
| `fix` | Исправление ошибки |
| `docs` | Только документация |
| `style` | Форматирование, без изменения логики |
| `refactor` | Рефакторинг — не fix и не feat |
| `perf` | Улучшение производительности |
| `test` | Добавление/исправление тестов |
| `chore` | Обновление зависимостей, конфигурации |
| `ci` | Изменения в CI/CD |

### Области (scope)

`bot`, `backend`, `miniapp`, `nginx`, `docs`, `deps`, `infra`

### Примеры

```bash
# Хорошие сообщения:
feat(bot): add /suggest command for user idea submission
fix(bot): decrement quota counter on handler error
docs(api): add GraphQL subscription examples
perf(backend): add index on (date, time_start) for free-rooms query
refactor(miniapp): extract useSchedule hook from SchedulePage
chore(deps): update aiogram to 3.17.0

# Плохие сообщения:
fix stuff
update
WIP
исправил баг
```

### Breaking changes

```bash
feat(auth)!: change JWT payload structure

BREAKING CHANGE: JWT tokens now include 'jti' field.
All existing tokens will be invalidated on deploy.
```

---

## Процесс Pull Request

### Перед отправкой

1. **Синхронизироваться с upstream/main**
2. **Запустить линтер:** `ruff check . && ruff format --check .`
3. **Запустить тесты** (если есть): `pytest`
4. **Обновить документацию** если изменилось поведение
5. **Проверить, что `.env` и секреты не попали в коммит:** `git diff --cached`

### Заполните описание PR

```markdown
## Что делает этот PR

Краткое описание изменений.

## Зачем это нужно

Ссылка на issue: Closes #42

## Как тестировалось

- [ ] Локально через `make up`
- [ ] Отправил тестовые запросы боту
- [ ] Проверил новый эндпоинт через curl / GraphiQL

## Скриншоты (если применимо)

## Чеклист

- [ ] Код следует стандартам проекта (ruff clean)
- [ ] Тесты добавлены / обновлены
- [ ] Документация обновлена
- [ ] CHANGELOG.md обновлён
- [ ] Секреты не попали в коммит
```

### Что происходит после отправки

```
PR создан
    │
    ├── Автоматические проверки (CI):
    │   ├── ruff check
    │   ├── mypy
    │   ├── pytest
    │   └── docker build (smoke test)
    │
    ├── Code Review (1+ approvals required)
    │   └── Ответить на комментарии или обновить код
    │
    └── Merge в main → автодеплой (если настроен CI/CD)
```

> [!NOTE]
> Reviewer'ы могут попросить изменений. Это нормально! Цель — получить качественный код, а не быстро слить. Отвечайте на все комментарии, даже если это просто `Done` или `Disagree, because...`

---

## Тестирование

### Структура тестов [предположение / требует уточнения]

```
tests/
├── backend/
│   ├── test_graphql.py     # GraphQL resolver tests
│   ├── test_rest_api.py    # REST endpoint tests
│   └── test_scraper.py     # Scraper logic tests
├── bot/
│   ├── test_intents.py     # Intent extraction tests
│   ├── test_normalizer.py  # Group name normalization
│   └── test_middleware.py  # Flood + quota middleware
└── conftest.py             # Shared fixtures
```

### Запуск тестов

```bash
# Все тесты:
cd ecampus_bot
pytest

# С покрытием:
pytest --cov=app --cov-report=term-missing

# Конкретный файл:
pytest tests/bot/test_intents.py -v

# Конкретный тест:
pytest tests/bot/test_normalizer.py::test_latin_group_name -v
```

### Пример теста

```python
# tests/bot/test_normalizer.py
import pytest
from app.bot.handlers.ai_handler import _normalize_group_for_query

@pytest.mark.parametrize("raw,expected", [
    ("исс б о 22 3",   "исс-б-о-22-3"),
    ("ISS-b-o-22-3",  "исс-б-о-22-3"),
    ("аис25",         "аис-б-о-25"),
    ("ИСС  Б О 22-3", "ИСС-б-о-22-3"),
    ("аис222",        "аис-б-о-22-2"),
])
def test_normalize_group(raw: str, expected: str):
    result = _normalize_group_for_query(raw)
    assert result is not None
    assert result.lower() == expected.lower(), f"Got: {result}"

def test_normalize_preserves_none():
    assert _normalize_group_for_query(None) is None

def test_normalize_short_input():
    # Слишком короткий → возвращает оригинал
    result = _normalize_group_for_query("аб")
    assert result == "аб"
```

### Тестирование с реальной БД

```python
# conftest.py
import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()

@pytest.fixture(scope="session")
async def test_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    await init_beanie(
        database=client["test_ncfu"],
        document_models=[LessonDoc, Group, Teacher, Room]
    )
    yield client["test_ncfu"]
    await client.drop_database("test_ncfu")
    client.close()
```

---

## Документация

Если ваши изменения затрагивают поведение системы — обновите соответствующий документ:

| Изменение | Документ для обновления |
|---|---|
| Новый API-эндпоинт | `API.md` |
| Новая команда бота | `USER_GUIDE.md` + `API.md` |
| Изменение архитектуры | `ARCHITECTURE.md` |
| Новая переменная окружения | `DEVELOPER_GUIDE.md` + `.env.example` |
| Исправление ошибки | `CHANGELOG.md` |
| Новая фича | `CHANGELOG.md` + профильный документ |

### Обновление CHANGELOG.md

Добавляйте запись в секцию `[Unreleased]` в начале файла:

```markdown
## [Unreleased]

### Added
- feat(bot): новая команда `/exam` для расписания экзаменов

### Fixed
- fix(bot): счётчик квоты больше не уменьшается при ошибке бэкенда
```

---

## Чек-лист перед отправкой PR

Перед тем как нажать «Create Pull Request», проверьте каждый пункт:

```
Код:
  [ ] ruff check . — нет ошибок
  [ ] ruff format --check . — нет нарушений форматирования
  [ ] mypy app/ — нет ошибок типов (или новые исключения задокументированы)
  [ ] pytest — все тесты проходят

Безопасность:
  [ ] git log --oneline -5 — нет секретов в коммитах
  [ ] .env файл не в diff
  [ ] /etc/ncfu/secrets не упоминается в коде

Документация:
  [ ] CHANGELOG.md обновлён
  [ ] Документация обновлена (если изменилось поведение)
  [ ] .env.example обновлён (если добавлены переменные)

PR:
  [ ] Описание PR заполнено
  [ ] Issue указан в Closes #N
  [ ] Ветка синхронизирована с upstream/main
  [ ] CI checks проходят (зелёный статус)
```

---

## Помощь и вопросы

- **Вопросы по коду** → создайте Discussion на GitHub
- **Нашли баг** → создайте Issue
- **Нужна помощь с настройкой** → см. [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Вопросы по архитектуре** → см. [ARCHITECTURE.md](ARCHITECTURE.md)

Спасибо, что помогаете делать бот лучше! 🎓
