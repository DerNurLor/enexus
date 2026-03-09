# NCFU Dashboard v2 — React Frontend

Полностью переработанный React-фронтенд для admin-панели dashboard2, заменяющий монолитный HTML-файл (4496 строк) на модульную React-архитектуру.

## Стек

| Технология | Версия | Назначение |
|---|---|---|
| React | 18.3 | UI компоненты + hooks |
| Vite | 5.x | Сборка, dev-server, HMR |
| TypeScript | 5.x | Типизация, безопасность |
| Framer Motion | 11.x | Анимации, переходы |
| Zustand | 4.x | Глобальный стейт (auth, UI) |
| TanStack Query | 5.x | Fetching, кэш, race conditions |
| Axios | 1.x | HTTP + interceptors |
| Recharts | 2.x | Графики и аналитика |
| react-helmet-async | 2.x | SEO/security meta tags |

## Структура

```
src/
├── api/
│   └── client.ts          # Axios + все API endpoints (типизированы)
├── components/
│   ├── charts/            # LineChart, BarChart, Heatmap, HorizBar
│   ├── common/            # Spinner, Avatar, Toast, Pagination, DetailPanel…
│   │   └── Icons.tsx      # SVG иконки (50+)
│   └── layout/
│       ├── Sidebar.tsx    # Боковая навигация с collapse
│       └── Topbar.tsx     # Верхняя панель + refresh + cache invalidate
├── pages/
│   ├── AuthGate.tsx       # Ввод токена / bootstrap login
│   ├── Overview/          # Общая статистика, графики
│   ├── Analytics/         # Детальная аналитика с вкладками
│   ├── Users/             # Список + детали + редактирование
│   ├── Chats/             # Чат с polling, медиа, поиск
│   ├── Support/           # Тикеты + ответ + закрытие
│   ├── Broadcast/         # Рассылка + история
│   ├── Roles/             # Роли + права (drag&drop редактор)
│   ├── Logs/              # Activity + Error logs с фильтрами
│   ├── Mongo/             # MongoDB viewer с JSON-фильтрами
│   └── Settings/          # Системные настройки
├── store/
│   ├── auth.ts            # Zustand auth store (token, user)
│   └── ui.ts              # Zustand UI store (panel, toasts, refresh)
├── styles/
│   └── global.css         # Design system CSS variables
├── types/
│   └── index.ts           # Все TypeScript интерфейсы
└── utils/
    └── helpers.ts         # Форматирование дат, чисел, escaping
```

## Установка и запуск

```bash
npm install
npm run dev    # localhost:3001 с proxy → localhost:8000
npm run build  # dist/ для деплоя
```

## Интеграция с бэкендом

Добавить в `dashboard2/app/dashboard/router.py`:

```python
# Вместо старого admin_panel:
@router.get("/admin", response_class=FileResponse, include_in_schema=False)
async def admin_panel_react(secret: str | None = Query(default=None)):
    # ... inject bootstrap token как раньше
    return FileResponse("dist/index.html")

# Статика React build:
app.mount("/dashboard/assets", StaticFiles(directory="dist/assets"), name="dashboard-assets")
```

Или использовать Nginx для раздачи `dist/`:
```nginx
location /dashboard/admin {
    root /path/to/dashboard2/dist;
    try_files $uri /index.html;
}
location /dashboard/assets/ {
    root /path/to/dashboard2/dist;
}
```

## Исправленные баги из HTML версии

1. **Race condition в autocomplete** → TanStack Query с `keepPreviousData`
2. **Дублирование resetQuota** (функция была объявлена дважды) → исправлено
3. **XSS в innerHTML** → dangerouslySetInnerHTML только для html_text из сервера, остальное — text nodes
4. **Потеря токена при 401** → interceptor с однократным retry
5. **Глобальные переменные `TOK`, `PREFIX`** → Zustand stores
6. **Bootstrap token в localStorage** → только в памяти (Zustand persist с `partialize`)
7. **Media URL SSRF** → валидация `file_id` на клиенте (alphanumeric + - + _)
8. **Нет loading state при смене панели** → AnimatePresence + motion.div
9. **Отсутствие debounce на поиске** → 300ms debounce через queryKey
10. **CSP**: добавлен `noindex, nofollow` мета и `X-Content-Type-Options`

## Безопасность (OWASP API Top 10)

- **API1**: Broken Object Level Authorization → все запросы идут через авторизованный клиент
- **API2**: Broken Authentication → token stored in Zustand (not window), interceptor на 401
- **API3**: Broken Object Property Level Exposure → только нужные поля отображаются
- **API6**: Unrestricted Access to Sensitive Business Flows → broadcast + admin actions через API
- **API8**: Security Misconfiguration → CSP meta tags, noindex
- **API10**: Unsafe Consumption of APIs → все ответы типизированы через TypeScript интерфейсы
