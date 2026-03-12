# Изменения: замена miniapp → web + профиль с TG-данными

## Что изменилось

### 1. Бот (ecampus_bot) — уже было сделано в репо
`/miniapp` → `WEB_URL` во всех командах:
- `cmd_miniapp()` — кнопка WebApp теперь ведёт на `settings.web_url`
- `cmd_about()` — ссылка на web-портал
- `bot_added_to_group()` — кнопка при добавлении в группу
- `BOT_COMMANDS` — описание команды `/miniapp` обновлено

Убедись что в `/etc/ncfu/secrets` задан `WEB_URL=https://app.enexus.isabelline.xyz`

---

### 2. web/lib/auth.ts — полная переработка
**Было:** POST `/miniapp/auth` (старый endpoint miniapp), только in-memory token, нет refresh.

**Стало:**
- POST `/auth/telegram/login` — правильный endpoint с `init_data`
- Refresh token в `localStorage` (ключ `ncfu_refresh_token`) — переживает перезагрузку браузера
- Тихий рефреш при открытии в обычном браузере (без initData)
- Параллельная загрузка: `/auth/me` + `/miniapp/api/settings` + `/miniapp/api/favorites`
- Экспортирует: `saveSettingsToServer`, `loadSettingsFromServer`, `fetchQuota`, `addFavorite`, `removeFavorite`

---

### 3. web/lib/store.ts — расширение состояния
**Добавлено:**
- `tgUser: TgUserInfo | null` — данные из `/auth/me` (tg_id, username, first_name, last_name, photo_url, roles)
- `authToken: string | null` — JWT в памяти (НЕ персистируется в localStorage)
- `tgAuthReady: boolean` — флаг завершения инициализации
- `isAuthenticated: boolean` — true если есть JWT
- `favorites: FavoriteItem[]` — синхронизируется с сервером
- `settings: UiSettings` — weekFromMonday, time24h, compact, theme, accent_color
- `applyServerSettings(s)` — мержит серверные настройки + восстанавливает profile из server settings

**Персистируется в localStorage** (ключ `ncfu-schedule`):
- profile, profileComplete, tgUser (кеш для быстрого рендера), favorites, settings

**НЕ персистируется:** authToken, tgAuthReady

---

### 4. web/components/Providers.tsx
Упрощён: убрана дублирующая логика инициализации TG SDK (теперь в auth.ts).
Добавлена передача `favorites` в store после авторизации.
Работает в обоих режимах: TG Mini App и обычный браузер.

---

### 5. web/app/profile/page.tsx — полная переработка
**Новые возможности:**

#### TG-профиль (только при наличии JWT)
- Аватар (фото из TG или инициалы)
- Имя (first_name + last_name)
- Username (@handle)
- Значки ролей (user/beta/vip/moderator/admin с цветами)

#### Лимит запросов к ИИ
- Прогресс-бар с процентом использования
- Цвет меняется: зелёный → оранжевый (70%) → красный (100%)
- Счётчик "X / Y" и "Сброс через Xч Yм"
- Auto-refresh каждые 60 секунд
- Если не авторизован — подсказка "Войдите через Telegram"

#### Настройки (синхронизируются с сервером)
- Неделя с понедельника
- 24-часовой формат
- Компактный вид
- Тема (авто/светлая/тёмная) с иконками
- Debounce 800ms перед сохранением на сервер
- Если не авторизован — хранятся только локально

#### Профиль расписания (студент/преподаватель)
- Сохраняется в `/miniapp/api/settings` под ключами `profile_role`, `profile_group_id`, `profile_group_name`, `profile_teacher_id`, `profile_teacher_name`
- При авторизации восстанавливается из серверных настроек (если локально нет)
- При сбросе — очищается и на сервере

#### Сценарии отображения
1. **TG Mini App, авторизован, профиль настроен** → TG-блок + профиль расписания + квота + настройки
2. **TG Mini App, авторизован, профиль не настроен** → TG-блок + квота + настройки + кнопка настроить
3. **Браузер, сохранён refresh token, профиль настроен** → TG-блок + профиль расписания + квота + настройки
4. **Анонимный браузер** → экран приветствия + настройки локально

---

## Что нужно проверить перед деплоем

### Секреты
В `/etc/ncfu/secrets` должны быть:
```bash
WEB_URL=https://app.enexus.isabelline.xyz
# Для staging:
# WEB_URL=https://app.staging.enexus.isabelline.xyz
```

### Nginx CORS
`/auth/*` проксируется на `miniapp:8002`. Web-портал (`app.*`) делает запросы на `api.*` (или тот же домен).
Убедись, что в `miniapp/.env` (или docker-compose env) `CORS_ALLOWED_ORIGINS` включает оба домена:
```
CORS_ALLOWED_ORIGINS=https://app.enexus.isabelline.xyz,https://app.staging.enexus.isabelline.xyz
```

### Telegram WebApp домен
В BotFather → Bot Settings → Domain — добавь `app.enexus.isabelline.xyz` как разрешённый домен для WebApp.
Без этого `initData` будет пустым при открытии через кнопку бота.

### Деплой
```bash
# Prod
make deploy  # или deploy.sh

# Если только web изменился:
docker compose build web && docker compose up -d web
```

---

## Схема потока авторизации

```
Пользователь нажимает кнопку в боте
         │
         ▼
Открывается app.enexus.isabelline.xyz
         │
         ▼
Providers.tsx → TgAuthInit.useEffect()
         │
         ├─ isTelegramWebApp() == true
         │      │
         │      ▼
         │  window.Telegram.WebApp.initData
         │      │
         │      ▼
         │  POST /auth/telegram/login { init_data }
         │      │
         │      ▼
         │  ← { access_token, refresh_token }
         │      │
         │  localStorage.set('ncfu_refresh_token', refresh)
         │      │
         │  Параллельно:
         │  GET /auth/me → TgUserInfo
         │  GET /miniapp/api/settings → profile + UI настройки
         │  GET /miniapp/api/favorites → избранное
         │      │
         │      ▼
         │  store.setTgUser(user)
         │  store.applyServerSettings(settings)  ← восстанавливает profile
         │  store.setFavorites(favorites)
         │
         └─ isTelegramWebApp() == false (обычный браузер)
                │
                ▼
            localStorage.get('ncfu_refresh_token')
                │
                ├─ есть → POST /auth/refresh → новый access_token
                │                            → те же 3 параллельных запроса
                │
                └─ нет → анонимный режим (profile из localStorage)
```
