# НЦФУ — Студенческий портал

PWA веб-приложение для студентов: расписание, новости, личный кабинет.

## Стек
- **Next.js 15** — SSR + App Router
- **Tailwind CSS** — стилизация
- **TanStack Query** — запросы к API
- **Zustand** — стейт
- **next-pwa** — PWA (установка на телефон/ПК)

## Разработка

```bash
npm install
npm run dev
# → http://localhost:3000
```

## Деплой в Docker

```bash
docker build -t ncfu_web .
```

В `docker-compose.yml` добавить сервис:

```yaml
web:
  image: ncfu_web:latest
  container_name: ncfu_web
  restart: unless-stopped
  environment:
    NEXT_PUBLIC_API_URL: "https://enexus.isabelline.xyz"
  ports:
    - "127.0.0.1:3000:3000"
  networks: [ncfu_net]
```

В nginx добавить:

```nginx
server {
    server_name app.enexus.isabelline.xyz;
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Структура

```
app/
  layout.tsx          — корневой layout (sidebar/mobile nav)
  schedule/page.tsx   — расписание
  news/page.tsx       — новости
  profile/page.tsx    — профиль / авторизация
  map/page.tsx        — карта
components/
  layout/
    MobileNav.tsx     — нижняя навигация (только мобайл)
    DesktopSidebar.tsx — боковая панель (ПК)
    PageHeader.tsx    — заголовок страницы
  schedule/
    LessonCard.tsx    — карточка занятия
    DayPicker.tsx     — выбор дня недели
  news/
    NewsCard.tsx      — карточка новости
  ui/
    PillTabs.tsx      — фильтр-таблетки
styles/
  globals.css         — CSS-переменные, шрифты, анимации
```

## PWA

После деплоя браузер автоматически предложит «Установить приложение».  
Иконки нужно добавить в `public/icons/icon-192.png` и `icon-512.png`.
