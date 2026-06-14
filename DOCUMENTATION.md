# NCFU Schedule — Full Project Documentation

> **СКФУ Расписание** — an intelligent scheduling platform for North Caucasus Federal University (NCFU / СКФУ). The system scrapes the university's eCampus portal, stores schedules in MongoDB, and delivers them via REST API, GraphQL, a Telegram bot, a Telegram Mini App, and a PWA student portal.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Project Structure](#3-project-structure)
4. [Services](#4-services)
   - [Backend (API + Scraper)](#41-backend---api--scraper)
   - [Bot (Telegram AI Bot)](#42-bot---telegram-ai-bot)
   - [MiniApp (Telegram Mini App)](#43-miniapp---telegram-mini-app)
   - [Dashboard (Admin Panel)](#44-dashboard---admin-panel)
   - [Web (PWA Student Portal)](#45-web---pwa-student-portal)
5. [Infrastructure](#5-infrastructure)
   - [MongoDB](#51-mongodb)
   - [Redis](#52-redis)
   - [Nginx](#53-nginx)
6. [Data Flow](#6-data-flow)
7. [Key Algorithms](#7-key-algorithms)
8. [Authentication System](#8-authentication-system)
9. [eCampus Integration](#9-ecampus-integration)
10. [Configuration & Deployment](#10-configuration--deployment)
11. [File Reference](#11-file-reference)

---

## 1. System Overview

The platform solves a fundamental problem: NCFU's official eCampus portal is slow, mobile-unfriendly, and has no API. This project:

- **Scrapes** schedule data from ecampus.ncfu.ru automatically every hour
- **Stores** it in MongoDB for fast querying
- **Exposes** it via REST, GraphQL, and the Telegram ecosystem
- **Enriches** it with AI (GPT-4o-mini powered natural-language queries in the bot)
- **Syncs** personal academic records (grades, transcripts) from eCampus per-user

**Users**: Students and faculty of NCFU / СКФУ

---

## 2. Architecture

```
                              ┌─────────────────────────────────────────┐
                              │              Nginx (port 8080)           │
                              │  Single entry point — routes by path     │
                              └────────────────────┬────────────────────┘
                                                   │
              ┌────────────────┬──────────────────┼──────────────────┬─────────────────┐
              │                │                  │                  │                 │
       /:port 8000      :8001 bot          :8002 miniapp     :8003 dashboard    :3000 web
              │                │                  │                  │                 │
     ┌────────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │    Backend     │ │   Bot        │ │  MiniApp     │ │  Dashboard   │ │  Next.js PWA │
     │  FastAPI       │ │  aiogram     │ │  FastAPI     │ │  FastAPI     │ │  React/TW    │
     │  REST + GQL    │ │  + OpenAI    │ │  + React SPA │ │  + React SPA │ │  Student UI  │
     └────────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
              │                │                  │                  │                 │
              └────────────────┴──────────────────┴──────────────────┴─────────────────┘
                                                   │
                           ┌───────────────────────┼───────────────────────┐
                           │                       │                       │
                    ┌──────────────┐      ┌──────────────┐        ┌───────────────┐
                    │   MongoDB    │      │    Redis     │        │  ecampus.ncfu │
                    │  ncfu_schedule│      │ Cache + RL  │        │  (scraped)    │
                    │  ncfu_auth   │      │             │        └───────────────┘
                    └──────────────┘      └──────────────┘
```

### Key Design Decisions

| Decision | Why |
|---|---|
| Separate services (backend/bot/miniapp/dashboard) | Independent scaling, failure isolation, clear responsibility boundaries |
| Shared MongoDB | Services communicate via DB, no internal RPC needed for schedule data |
| Redis | Sub-millisecond cache + rate limiting shared across services |
| GraphQL + REST dual API | GraphQL for bots/external consumers, REST for web PWA (simpler, faster) |
| Beanie ODM | Async-native MongoDB access with Pydantic schemas |
| APScheduler | Reliable hourly scraping with cron-based cleanups |

---

## 3. Project Structure

```
/opt/ncfu/
├── backend/                    # Core API service (FastAPI, port 8000)
│   └── app/
│       ├── main.py             # App factory, lifespan, middleware
│       ├── core/               # Config, logging, observability, rate limiting
│       ├── api/routes/         # REST API route handlers
│       ├── auth/               # JWT auth, Telegram login, API keys
│       ├── cache/              # Redis client wrapper
│       ├── db/                 # MongoDB connection (schedule data)
│       ├── dashboard/          # Admin dashboard backend + SPA files
│       ├── ecampus/            # eCampus client, sync, queue, captcha
│       ├── graphql/            # Strawberry GraphQL schema, resolvers, types
│       ├── models/             # Schedule domain models (beanie Documents)
│       ├── scheduler/          # APScheduler jobs
│       ├── scraper/            # Scraper pipeline (institutes→groups→schedules)
│       ├── scripts/            # One-off migration scripts
│       └── search/             # Full-text search service
│
├── ecampus_bot/                # Telegram bot service (aiogram, port 8001)
│   └── app/
│       ├── main.py             # FastAPI wrapper, webhook endpoint
│       ├── bot/                # Bot setup, dispatcher, handlers, AI pipeline
│       │   ├── handlers/       # Command handlers + AI message handler
│       │   ├── middlewares/    # Anti-flood, quota, webhook rate limiting
│       │   ├── conversation.py # Per-user conversation history (Redis)
│       │   ├── intents.py      # Pydantic intent models for OpenAI extraction
│       │   └── message_store.py# Persist every user↔bot message to MongoDB
│       ├── auth/               # Auth models (shared schema with backend)
│       ├── cache/              # Redis client
│       └── core/               # Config, logging, rate limiting
│
├── miniapp/                    # Telegram Mini App service (FastAPI, port 8002)
│   └── app/
│       ├── main.py             # FastAPI app, serves React SPA
│       ├── miniapp/            # Schedule API, quota, React build files
│       ├── auth/               # TG initData validation, JWT, widget auth
│       ├── graphql/            # GraphQL client (queries backend)
│       └── search/             # Search service
│   └── react-src/              # React 18 + Vite source for Mini App UI
│       └── src/
│           ├── App.tsx         # Root component + bottom nav
│           ├── pages/          # SchedulePage, RoomsPage, FavoritesPage, ProfilePage
│           └── utils/api.ts    # API client
│
├── dashboard/                  # Admin dashboard service (FastAPI, port 8003)
│   └── app/
│       ├── main.py             # FastAPI app
│       └── dashboard/          # Conversations, media, broadcast API
│   └── react/                  # React 18 + Vite admin SPA source
│       └── src/pages/          # Analytics, Chats, Users, Logs, Broadcast, Settings
│
├── web/                        # Student PWA portal (Next.js 14, port 3000)
│   ├── app/                    # Next.js App Router pages
│   │   ├── schedule/page.tsx   # Main schedule view (group/teacher/room)
│   │   ├── ecampus/page.tsx    # eCampus personal grades page
│   │   ├── map/page.tsx        # Campus map / free rooms
│   │   ├── rooms/page.tsx      # Room lookup
│   │   ├── profile/page.tsx    # User profile + settings
│   │   └── news/page.tsx       # University news feed
│   ├── components/             # UI components
│   │   ├── schedule/           # LessonCard, DayPicker, SearchDropdown, TeacherDashboard
│   │   ├── ecampus/            # ECampusSection, ECampusAdminSection, ProfileModals
│   │   ├── layout/             # DesktopSidebar, MobileNav, PageContainer, PageHeader
│   │   └── ui/                 # PillTabs, PWAInstallBanner
│   ├── lib/
│   │   ├── api.ts              # HTTP client for backend REST API
│   │   ├── auth.ts             # Telegram initData login, JWT management
│   │   ├── store.ts            # Zustand global state (search state, profile, auth)
│   │   └── types.ts            # TypeScript interfaces for all API data
│   ├── hooks/useGestures.ts    # Touch swipe gesture detection
│   └── styles/globals.css      # CSS custom properties, dark theme tokens
│
├── nginx/
│   ├── nginx.conf.template     # Nginx config template (envsubst at startup)
│   └── entrypoint.sh           # Nginx entrypoint — substitutes env vars
│
├── docker/
│   └── mongo/init.js           # MongoDB init script (creates users/DBs)
│
├── docker-compose.yml          # Production stack (7 services)
├── docker-compose.dev.yml      # Development overrides
├── docker-compose.staging.yml  # Staging configuration
├── deploy.sh                   # Deployment script (build → push → pull → up)
├── setup-secrets.sh            # Secret generation helper
├── Makefile                    # Developer convenience targets
└── .env / .env.example         # Environment variables
```

---

## 4. Services

### 4.1 Backend — API + Scraper

**File**: `backend/app/main.py`  
**Port**: `8000`  
**Tech**: FastAPI 0.111, Beanie 2.0, APScheduler, Strawberry GraphQL, Prometheus

The core service. It does four things:
1. Serves the REST API for schedule data
2. Serves the GraphQL API
3. Runs the scraper pipeline on a schedule
4. Hosts the admin dashboard SPA

#### Startup sequence (`lifespan`):
```python
setup_observability()       # Loguru + OpenTelemetry + Sentry
await connect_db()          # MongoDB ncfu_schedule
await connect_auth_db()     # MongoDB ncfu_auth
await init_redis()
setup_scheduler()           # APScheduler (scrape, cleanup, ecampus sync)
await start_ecampus_worker()# eCampus async queue worker
await ensure_campuses_loaded()  # Pre-load campus data if empty
```

#### Middleware stack:
1. **HTTPSEnforceMiddleware** (prod) — redirects HTTP → HTTPS, sets HSTS
2. **CORSMiddleware** — whitelist from `CORS_ALLOWED_ORIGINS`, always includes Telegram web domains
3. **GlobalRateLimitMiddleware** — per-IP (anon) or per-user (JWT) rate limiting via Redis sliding window

#### REST API routes (`backend/app/api/routes/`):

| File | Prefix | Description |
|---|---|---|
| `schedules.py` | `/schedules/` | Group/teacher/room day and week schedules |
| `search.py` | `/search/` | Full-text search for groups, teachers, rooms |
| `groups.py` | `/groups/` | Group listing and metadata |
| `teachers.py` | `/teachers/` | Teacher listing, stats, today's rooms |
| `rooms.py` | `/rooms/` | Room listing, free rooms at a given time |
| `institutes.py` | `/institutes/` | Institute listing with buildings |
| `overview.py` | `/overview/` | System totals and scrape health |
| `scrape.py` | `/scrape/` | Trigger manual scrape |
| `campuses.py` | `/campuses/` | Campus/building data |

All routes are also mounted at `/api/v1/` for versioned access.

#### GraphQL API (`backend/app/graphql/`)

Built with **Strawberry**. Exposes Query, Mutation, and Subscription types.

**Security extensions**:
- `QueryDepthLimiter` (max depth 5) — prevents N+1 resource exhaustion attacks
- `MaxTokensLimiter(1000)` — caps document size against token-flood DoS

**Key queries**:
```graphql
query {
  groupSchedule(groupName: "ИСС-б-о-22-3", week: 24) { date lessons { subject timeStart } }
  teacherSchedule(teacherName: "Иванов И.И.", fromDate: "2026-06-14") { ... }
  freeRooms(at: "2026-06-14T10:00", duration: 90, building: "11") { name building }
  search(q: "физика") { groups { name } teachers { fullName } }
  overview { groupsTotal lastScrapeStatus }
}
mutation { triggerScrape(mode: "incremental") { status groupsScraped } }
subscription { scheduleUpdated(groupId: 123) { groupId date status } }
```

#### Scheduler (`backend/app/scheduler/scheduler.py`)

Uses APScheduler with `AsyncIOScheduler`. Jobs:

| Job | Trigger | Purpose |
|---|---|---|
| `hourly_scrape` | Every `SCRAPE_INTERVAL_HOURS` (default 1h) | Scrape schedule from eCampus |
| `daily_log_cleanup` | Cron `03:00 UTC` | Delete old auth logs (TTL: 90 days) |
| `daily_ecampus_sync` | Cron `03:00 UTC` | Sync all users' eCampus data |
| `retry_failed_ecampus_syncs` | Every 2h | Retry failed eCampus syncs with backoff |
| `daily_campus_sync` | Cron `04:30 UTC` | Refresh campus/building data |
| `profile_sync_3d` | Every 3 days | Refresh student profile details |

On startup, first scrape runs 5 seconds after app boot.

---

### 4.2 Bot — Telegram AI Bot

**File**: `ecampus_bot/app/main.py`  
**Port**: `8001`  
**Tech**: aiogram 3.x, OpenAI GPT-4o-mini via `instructor`, httpx

Receives Telegram webhooks, extracts user intent with GPT-4o-mini, queries the backend GraphQL API, and formats the reply.

#### Webhook security:
```python
# HMAC verification on every webhook update
secret = settings.get_telegram_webhook_secret()
token_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
if not hmac.compare_digest(token_header, secret):
    return Response(status_code=403)
```

#### AI Pipeline (`ecampus_bot/app/bot/handlers/ai_handler.py`):

```
User message
      │
      ▼
[Redis intent cache check]  →  HIT → return cached reply
      │ MISS
      ▼
[OpenAI GPT-4o-mini]  →  IntentResponse (structured via instructor)
      │
      ▼
[Intent dispatch]
 ├── GroupScheduleIntent     → GQL groupSchedule query
 ├── TeacherScheduleIntent   → GQL teacherSchedule query
 ├── TeacherNowIntent        → GQL lessonsOn query (current time)
 ├── GroupNowIntent          → GQL lessonsOn + "what's happening now"
 ├── FreeRoomsIntent         → GQL freeRooms query
 ├── BuildingScheduleIntent  → per-room schedule aggregation
 ├── RoomScheduleIntent      → GQL roomSchedule query
 ├── SearchIntent            → GQL search + auto-redirect if 1 teacher
 ├── LessonsOnDayIntent      → GQL lessonsOn for specific date
 ├── OverviewIntent          → GQL overview
 ├── InstitutesIntent        → GQL institutes
 └── UnknownIntent           → clarification message
      │
      ▼
[Disambiguation] (if multiple groups/rooms match)
  → Store candidates in Redis → Show inline keyboard to user
      │
      ▼
[Paged response] (multi-day schedule)
  → Store pages in Redis → Show first page + navigation buttons
      │
      ▼
[Cache formatted reply in Redis]
      │
      ▼
[Send to user + feedback buttons 👍/👎]
      │
      ▼
[Store to MongoDB: ChatMessage, BotConversation]
```

#### Group name normalization:
The `_normalize_group_for_query` function converts any variant of group name to a searchable form:
- `"исс222"` → `"исс-б-о-22-2"`
- `"ISS-b-o-22-3"` (latin) → `"исс-б-о-22-3"` (cyrillic)
- `"ИСС  Б О 22 3"` → `"исс-б-о-22-3"`

Uses transliteration + regex normalization + form alias mapping (`bak`→`б`, `mag`→`м`).

#### Reply caching TTLs (Redis):
```
group_now / teacher_now / free_rooms: 60–120s (changes every lesson slot)
group_schedule / teacher_schedule:    600s
building_schedule:                    300s
institutes:                           3600s
```

#### Bot commands:

| Command | Handler | Purpose |
|---|---|---|
| `/start` | `extra_handlers.py` | Welcome message |
| `/help` | `extra_handlers.py` | Command list |
| `/roles` | `commands.py` | Show user roles and permissions |
| `/support <text>` | `commands.py` | Create support ticket |
| `/suggest <text>` | `commands.py` | Submit feature suggestion |
| `/limit` | `commands.py` | Show AI query quota and reset time |
| `/about` | `commands.py` | Bot info + version |
| `/miniapp` | `commands.py` | Open Mini App button |
| `/me` | `extra_handlers.py` | View eCampus profile |
| `/teacher` | `extra_handlers.py` | Teacher schedule lookup |
| `/classmates` | `extra_handlers.py` | Group schedule lookup |

#### Anti-flood middleware (`bot/middlewares/anti_flood.py`):
Per-user quota counted in Redis. Separate limits for:
- Private chats: `QUOTA_PRIVATE` requests per `QUOTA_TTL_HOURS` hours
- Small groups: `QUOTA_GROUP_SMALL`
- Large groups: `QUOTA_GROUP_LARGE`

---

### 4.3 MiniApp — Telegram Mini App

**File**: `miniapp/app/main.py`  
**Port**: `8002`  
**Tech**: FastAPI + React 18 + Vite

Serves a React SPA as a Telegram Mini App. Authentication via Telegram `initData` HMAC validation → JWT.

#### Python API endpoints (`miniapp/app/miniapp/router.py`):
- `GET /miniapp/` — serve `index.html` (React SPA root)
- `GET /miniapp/api/schedule/{group_id}/day` — day schedule
- `GET /miniapp/api/schedule/{group_id}/week` — week schedule
- `GET /miniapp/api/rooms/free` — free rooms query
- `GET /miniapp/api/favorites` / `POST` / `DELETE` — favorites management
- `GET /miniapp/api/profile/limits` — quota status for current user
- `GET /miniapp/api/profile/settings` — user UI settings (server-side)

#### Auth flow:
1. `POST /auth/telegram/login` with Telegram `initData`
2. Server validates HMAC with `BOT_TOKEN`
3. Returns JWT access + refresh tokens
4. Frontend stores JWT in memory (not localStorage for security)
5. Subsequent requests use `Authorization: Bearer <token>`

#### React Mini App (`miniapp/react-src/`):
Built with Vite, deployed as static files embedded in the Python package.

**Pages**:
- **SchedulePage** — search groups/teachers/rooms, day-level schedule
- **RoomsPage** — free rooms lookup with building filter
- **FavoritesPage** — saved groups/teachers
- **ProfilePage** — user settings, eCampus login

---

### 4.4 Dashboard — Admin Panel

**File**: `dashboard/app/main.py`  
**Port**: `8003`  
**Tech**: FastAPI + React 18 + Vite

Internal admin SPA. Accessible only via the secret `ADMIN_PATH` prefix in Nginx (e.g. `/edY5N875HC99/dashboard/admin`).

#### Backend API (`dashboard/app/dashboard/`):

| File | Purpose |
|---|---|
| `router.py` | SPA catch-all, serves `index.html` |
| `api.py` | Stats overview, user management, broadcast, scrape control |
| `api_chats.py` | Chat history viewer, support tickets |
| `conversations.py` | Conversation retrieval per user |
| `media_service.py` | On-demand media file fetching from Telegram |
| `message_utils.py` | Message formatting utilities |

#### React Admin SPA (`dashboard/react/`):

**Pages**:
- **Overview** — system stats, scrape status, uptime
- **Analytics** — charts: message volume, user growth, lesson stats
- **Users** — list/search/block users, role management
- **Chats** — conversation viewer per user (text + media preview)
- **Logs** — activity log viewer, error log viewer
- **Broadcast** — send messages to all/active/role users
- **Support** — support tickets (open/answered/closed)
- **Settings** — chat settings, rate limits
- **Mongo** — basic DB stats
- **Roles** — role/permission management

---

### 4.5 Web — PWA Student Portal

**File**: `web/`  
**Port**: `3000`  
**Tech**: Next.js 14 (App Router), React 18, Tailwind CSS, Zustand, TanStack Query

A Progressive Web App for students. Can be installed on home screen (PWA manifest + service worker). Separate subdomain: `app.<DOMAIN>`.

#### Pages:

##### `/schedule` — Main Schedule Page (`web/app/schedule/page.tsx`)
The most complex page. Features:
- **Search modes**: Group / Teacher / Room (pill tabs)
- **Live clock** (Moscow time, UTC+3) updated every second
- **Current/next lesson widget** — shows at the top of the page
- **Touch gestures** (via `useGestures.ts`):
  - Swipe left/right → next/prev day
  - Swipe up → jump to today
  - Edge swipe right → cycle search modes
- **Offline support** — lessons cached in localStorage (LRU eviction at 150 keys)
- **Week prefetch** — prefetches current + next week 3s and 8s after entity selection
- **Favorites** — star button saves groups/teachers via Mini App API
- **URL params** — deep links: `/schedule?mode=group&id=123&name=ИСС-б-о-22-3`
- **eCampus grades overlay** — if viewing own group and eCampus linked, shows grade badges on lessons
- **Profile auto-apply** — on mount, automatically selects own group/teacher from saved profile

##### `/ecampus` — Personal eCampus Integration (`web/app/ecampus/page.tsx`)
Allows students to link their eCampus account and view:
- Personal grade data per subject
- Grade transcript (зачётная книжка)
- Sync status and manual refresh

##### `/map` — Free Rooms Map (`web/app/map/page.tsx`)
Shows which classrooms are currently free across all buildings.

##### `/profile` — User Profile (`web/app/profile/page.tsx`)
- Role selection (student/teacher)
- Group/teacher binding
- UI settings (theme, compact mode, 24h time)
- eCampus account management

#### State Management (`web/lib/store.ts`):
Uses **Zustand** with `persist` middleware (localStorage key: `ncfu-schedule`).

**Persisted state**:
- `mode`, `groupId/Name`, `teacherId/Name`, `roomId/Name` — last search
- `profile` — user role + bound group/teacher
- `tgUser` — cached TG profile for fast render
- `favorites` — saved groups/teachers
- `settings` — UI preferences (theme, compact, time format)

**Not persisted**:
- `authToken` — re-issued on each login (security)
- `tgAuthReady` — runtime flag

#### API Client (`web/lib/api.ts`):
Thin fetch wrapper around the backend REST API. Base URL: `NEXT_PUBLIC_API_URL + /api`.

Two request modes:
- `get()` — anonymous (schedule data, no auth required)
- `authedGet()` — with `Authorization: Bearer` (quota status, favorites via miniapp)

#### Component Architecture:

```
web/components/
├── schedule/
│   ├── LessonCard.tsx         # Single lesson display with type color coding
│   ├── DayPicker.tsx          # Horizontal day scroll selector
│   ├── SearchDropdown.tsx     # Search results dropdown
│   └── TeacherDashboard.tsx   # Teacher-specific stats and room info
├── ecampus/
│   ├── ECampusSection.tsx     # Grade display per subject
│   ├── ECampusAdminSection.tsx# Admin-only eCampus data view
│   └── ProfileModals.tsx      # eCampus login/link modal dialogs
├── layout/
│   ├── ConditionalLayout.tsx  # Shows sidebar on desktop, mobile nav on mobile
│   ├── DesktopSidebar.tsx     # Left sidebar navigation (≥1024px)
│   ├── MobileNav.tsx          # Bottom tab bar (< 1024px)
│   ├── PageContainer.tsx      # Max-width content wrapper
│   └── PageHeader.tsx         # Page title + optional action slot
├── auth/
│   ├── TelegramAuthSection.tsx# Telegram Login Widget integration
│   └── TelegramLoginButton.tsx# Login button component
└── ui/
    ├── PillTabs.tsx           # Tab switcher (group/teacher/room)
    └── PWAInstallBanner.tsx   # Install to home screen prompt
```

---

## 5. Infrastructure

### 5.1 MongoDB

Two databases on the same MongoDB 7.0 instance:

**`ncfu_schedule`** — Schedule domain data:

| Collection | Model | Description |
|---|---|---|
| `institutes` | `Institute` | Universities/faculties with IDs and names |
| `groups` | `Group` | Student groups with speciality, course, institute |
| `teachers` | `Teacher` | Faculty members with subjects and groups |
| `rooms` | `Room` | Classrooms with building and capacity |
| `lessons` | Lesson (raw) | Individual lessons (date, time, subject, teacher, room, group) |
| `scrape_logs` | `ScrapeLog` | Per-run scraper metrics and errors |
| `ecampus_sync` | `ECampusSyncRecord` | Per-user eCampus credentials and synced data |

**`ncfu_auth`** — Authentication and user data:

| Collection | Model | Description |
|---|---|---|
| `auth_users` | `AuthUser` | User profiles (tg_id, roles, settings, favorites) |
| `auth_roles` | `AuthRole` | Role definitions with permission lists |
| `auth_api_keys` | `AuthApiKey` | Hashed API keys with rate limits |
| `auth_activity_log` | `AuthActivityLog` | User action audit trail (TTL: 90 days) |
| `auth_error_logs` | `AuthErrorLog` | Application errors with stack traces (TTL: 30 days) |
| `bot_conversations` | `BotConversation` | Per-user AI conversation history |
| `chat_messages` | `ChatMessage` | Full message store (every user↔bot exchange, TTL: 180 days) |
| `support_tickets` | `SupportTicket` | User support requests |
| `broadcast_jobs` | `BroadcastJob` | Bulk message send jobs |
| `auth_dpop_nonces` | `AuthDPoPNonce` | DPoP proof nonces (TTL: 10min) |

### 5.2 Redis

Used for:

| Key pattern | Purpose |
|---|---|
| `ncfu:*` | Schedule cache (invalidated after each scrape) |
| `rl:user:<uid>:<bucket>` | Per-user rate limit counter |
| `rl:anon:<ip>:<bucket>` | Per-IP rate limit counter |
| `bot:intent:<hash>:<minute>` | Intent extraction cache (avoids duplicate OpenAI calls) |
| `bot:reply:<type>:<hash>` | Formatted reply cache |
| `bot:pages:<uid>:<hash>` | Paginated schedule pages for navigation |
| `disambig:<uid>:<hash>` | Disambiguation state (multiple group matches) |
| `refresh:jti:<jti>` | JWT refresh token tracking (prevents token reuse) |
| `refresh:user:<uid>` | Current refresh JTI for user |
| `quota:<type>:<id>` | AI query quota counters |
| `ecampus:session:<tg_id>` | eCampus session cookies cache (TTL: 3h) |

Config: `--maxmemory 512mb --maxmemory-policy allkeys-lru`

### 5.3 Nginx

Acts as the single entry point (port 8080). Routes by URL path:

| Path | Upstream | Rate limit |
|---|---|---|
| `/webhook/telegram` | `bot:8001` | 100 req/s (webhook zone) |
| `/{ADMIN_PATH}/dashboard/*` | `dashboard:8003` | 60 req/min |
| `/auth/*` | `miniapp:8002` | 10 req/min |
| `/miniapp/*` | `miniapp:8002` | — |
| `/graphql` | `backend:8000` | 30 req/min |
| `/static/*` | `backend:8000` | Cache 1 day |
| `/*` (fallback) | `backend:8000` | 30 req/min |

Second server block handles `app.<DOMAIN>` → Next.js PWA:
- `/_next/static/` → 1 year cache
- `/api/` → proxied to backend
- `/*` → Next.js

Dashboard is hidden behind `ADMIN_PATH` — a random secret path set in `.env`. Direct access to `/dashboard/*` returns 403.

Security headers applied globally:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

---

## 6. Data Flow

### Schedule Scrape Flow

```
APScheduler (every 1h)
    │
    ▼
NCFUScraper.run()
    │
    ├─ Phase 1: INSTITUTES
    │  └─ GET /api/institutes for each branch (1, 2, 3)
    │     └─ Upsert into MongoDB institutes collection
    │
    ├─ Phase 2: GROUPS (Source of Truth)
    │  ├─ For each institute → GET /api/specialties
    │  └─ For each specialty → GET /api/groups
    │     └─ Upsert into MongoDB groups collection
    │
    ├─ Phase 3: SCHEDULES (smart diff-sync)
    │  ├─ For each group (10 concurrent, semaphore-limited):
    │  │  ├─ If fresh (<24h) → skip
    │  │  ├─ mode=incremental: fetch current + next 2 weeks
    │  │  └─ mode=full: scan backward (4-week empty limit) + forward
    │  │     └─ _flush_lessons_smart():
    │  │        ├─ Compute MD5 hash of existing lessons for that day
    │  │        ├─ If hash matches new data → skip (unchanged)
    │  │        └─ If different → delete day + insert new lessons
    │  ├─ Accumulate teachers and rooms from lessons
    │  │
    │  ├─ Phase 4: Entity stats (lesson counts per teacher/room)
    │  └─ Phase 5: Flush teachers + rooms to MongoDB
    │
    └─ Invalidate Redis cache: ncfu:*
       Publish to Redis channel: ncfu:scrape:completed
```

### User Schedule Request (Web PWA)

```
Browser → Nginx (:8080) → Next.js (:3000) [for HTML/JS]
                        ↓
Browser → /api/schedules/group/123/day?day=2026-06-14
                        ↓
Nginx → backend:8000
                        ↓
Redis cache check (key: ncfu:day:group:123:2026-06-14)
    HIT  → return cached JSON (TTL 60s)
    MISS → MongoDB query → cache + return
```

### Bot AI Query Flow

```
Telegram → POST /webhook/telegram → nginx → bot:8001
                        ↓
HMAC signature verification
                        ↓
aiogram dispatcher → handle_message()
                        ↓
Check Redis intent cache (key by text hash + minute)
    HIT  → check reply cache
    MISS → GPT-4o-mini (instructor structured extraction)
                        ↓
IntentResponse (GroupScheduleIntent | TeacherNowIntent | ...)
                        ↓
Check Redis reply cache (key by intent params)
    HIT  → send cached reply
    MISS → GraphQL query to backend:8000/graphql
                        ↓
Format response (HTML, Telegram-safe, ≤4096 chars per chunk)
Multi-day → store pages in Redis → paged navigation buttons
Multi-group → disambiguation keyboard
                        ↓
Edit placeholder message → send reply
Store: ChatMessage + BotConversation in MongoDB (async, non-blocking)
Add feedback buttons (👍/👎)
```

---

## 7. Key Algorithms

### 7.1 Diff-sync Schedule (`_flush_lessons_smart`)

The scraper uses content-addressed diffing to minimize database writes:

```python
# For each (group, date) pair:
new_hash = MD5(sorted_canonical_docs(new_lessons))
old_hash = MD5(sorted_canonical_docs(existing_lessons))

if new_hash == old_hash:
    # Nothing changed — skip expensive delete + insert
    unchanged += len(existing)
else:
    # Delete all lessons for this (group, date)
    # Insert new lessons
    written += len(new_lessons)
```

The canonical hash excludes `_id` and `scraped_at` fields (volatile) so that a re-scrape of identical data produces the same hash.

### 7.2 Intent Extraction System

Intent models are Pydantic classes extracted by `instructor` (OpenAI structured output):

```python
class GroupScheduleIntent(BaseModel):
    intent: Literal["group_schedule"]
    group_name: Optional[str]       # extracted verbatim from user text
    group_id: Optional[int]
    from_date: Optional[str]        # ISO date
    to_date: Optional[str]
    week: Optional[int]

class FreeRoomsIntent(BaseModel):
    intent: Literal["free_rooms"]
    time_ref: Optional[TimeRef]     # relative or absolute time
    duration_minutes: int = 90
    building: Optional[str]

class TimeRef(BaseModel):
    iso: Optional[str]              # exact ISO datetime
    offset_minutes: Optional[int]   # "+30 minutes"
    date_expr: Optional[str]        # "today", "tomorrow", "next_monday", "wednesday"
    time_of_day: Optional[str]      # "14:00"
```

`IntentResponse` is a discriminated union of all intent types:
```python
class IntentResponse(BaseModel):
    result: Annotated[
        GroupScheduleIntent | TeacherScheduleIntent | FreeRoomsIntent | ...,
        Field(discriminator="intent")
    ]
```

### 7.3 Rate Limiting

Sliding window algorithm using Redis atomic operations:

```python
# Bucket = current UNIX minute (window = 60s → 1 minute buckets)
bucket = int(time.time()) // window

# Per-user key: rl:user:<uid>:<bucket>
# Per-IP key:   rl:anon:<ip>:<bucket>
count = await redis.incr(key)
if count == 1:
    await redis.expire(key, window * 2)  # 2x window for safety
if count > rpm:
    raise HTTPException(429, "Rate limit exceeded")
```

### 7.4 eCampus Captcha Solving

The eCampus login page requires a captcha. The system:
1. Fetches the captcha image from `/Captcha/Captcha`
2. Encodes it as base64
3. Submits to 2captcha API (`/in.php`)
4. Polls for result every 5 seconds (max 2 minutes)
5. Uses the text result to submit the login form

Credentials stored AES-256-GCM encrypted in MongoDB. Sessions (cookies) cached in Redis with 3h TTL to avoid repeated captcha solving.

---

## 8. Authentication System

### JWT Flow

```
Telegram initData (signed by Telegram with BOT_TOKEN)
          ↓
POST /auth/telegram/login
    - Validate HMAC of initData
    - Upsert AuthUser (tg_id, name, username)
    - Check if blocked
    - TOTP check (if 2FA enabled)
    - Download avatar (background task)
          ↓
Return:
    access_token  (JWT, HS256, 1h TTL)
    refresh_token (JWT, HS256, 31d TTL, JTI tracked in Redis)
```

**JWT payload**:
```json
{
  "sub": "<mongodb_user_id>",
  "tg_id": 123456789,
  "roles": ["user"],
  "jti": "<uuid>",
  "exp": 1234567890
}
```

### Token Refresh

Refresh tokens use rotation (old JTI deleted from Redis, new one stored). Reuse of a revoked refresh token triggers a security warning.

### API Keys

Users can create API keys via `/auth/keys` (max 1000 rpm, optional expiry). Keys are stored as `SHA-256(key)` hash + 8-char prefix. The raw key is shown only once at creation.

### Permissions System

Roles (e.g. `user`, `vip`, `moderator`, `admin`) carry permission sets:
- `users:read` / `users:write`
- `logs:read`
- `admin:full`
- `beta_access`
- `floorplan:view` / `floorplan:edit`

Users also have `extra_permissions` (per-user overrides on top of role permissions).

### Production Validation

```python
@model_validator(mode="after")
def validate_production_secrets(self) -> "Settings":
    if self.app_env == "production":
        if not jwt_val or len(jwt_val) < 32:
            raise ValueError("JWT_SECRET must be ≥ 32 chars in production")
```

---

## 9. eCampus Integration

The eCampus integration lets students link their university account to see personal grades alongside their schedule.

### Per-user Sync Record (`ECampusSyncRecord`):
- `login_enc` / `password_enc` — AES-256-GCM encrypted credentials
- `session_cookies_json` — cached HTTP session (avoids captcha on each sync)
- `courses` — list of subjects with lessons and grades
- `zachetka` — full grade transcript
- `profile_details` — specialty, course, study form

### Sync Pipeline:

```
Student submits credentials (login + password)
          ↓
ECampusClient.authenticate()
    1. GET login page → extract CSRF token
    2. GET /Captcha/Captcha → solve via 2captcha
    3. POST login form with CSRF + captcha
    4. Validate redirect (not back to login page)
    5. Return cookies
          ↓
Store encrypted credentials + session in DB
          ↓
ECampusClient.get_studies_viewmodel() → semester list
ECampusClient.get_courses(student_id, term_id) → per-semester subjects
ECampusClient.get_lessons(lesson_type_id, student_id) → grades per lesson type
ECampusClient.get_zachetka() → full transcript (JSON from embedded JS viewModel)
ECampusClient.get_details() → student profile fields
          ↓
Store in ECampusSyncRecord.courses + .zachetka + .profile_details
          ↓
APScheduler triggers daily re-sync for all users with enabled=True
```

### Zachetka Parsing:
The transcript page embeds data as JavaScript: `var viewModel = {...}`. The client extracts it with regex, strips `JSON.parse("...")` wrapper, and normalizes nested `StudyYears → Terms → Exams/Zachets/Other` structures.

---

## 10. Configuration & Deployment

### Environment Variables

Key variables in `.env`:

```bash
# Infrastructure
MONGO_URI=mongodb://user:pass@mongo:27017/ncfu_schedule?authSource=admin
AUTH_MONGO_URI=mongodb://user:pass@mongo:27017/ncfu_auth?authSource=admin
REDIS_URL=redis://:password@redis:6379/0

# Security
JWT_SECRET=<64-char hex>        # Must be ≥32 chars in production
DASHBOARD_SECRET=<random>       # Admin dashboard password
GRAPHQL_SECRET=<random>         # GraphQL IDE access token
BOT_API_SECRET=<random>         # Internal bot→API auth
TELEGRAM_WEBHOOK_SECRET=<random> # Telegram webhook HMAC key

# Services
TELEGRAM_BOT_TOKEN=123:ABC      # Main bot
SUPPORT_BOT_TOKEN=              # Support notification bot (optional)
ADMIN_BOT_TOKEN=                # Admin command bot (optional)
WEBHOOK_BASE_URL=https://yourdomain.com
WEB_URL=https://app.yourdomain.com

# eCampus
TWOCAPTCHA_API_KEY=<key>        # 2captcha.com API key
ECAMPUS_ENCRYPTION_KEY=<64-hex> # AES-256 key for credential encryption

# Features
OPENAI_API_KEY=sk-...           # Optional (bot AI disabled without it)
SENTRY_DSN=https://...          # Optional error tracking
ADMIN_PATH=<random-string>      # Secret URL prefix for dashboard
APP_ENV=production              # or development

# Rate limiting
RATE_LIMIT_USER_RPM=300
RATE_LIMIT_ANON_RPM=120
QUOTA_PRIVATE=3                 # AI queries per TTL period (private chat)
QUOTA_GROUP_SMALL=3             # (group chat <50 members)
QUOTA_GROUP_LARGE=5             # (group chat ≥50 members)
QUOTA_TTL_HOURS=7               # Reset window
```

### Docker Stack

Production: `docker-compose.yml` (7 services)

```
make up          # Start all services
make down        # Stop all services
make logs        # Follow logs
make scrape      # Trigger manual scrape
make build       # Rebuild images
make restart     # Restart specific service (make restart SERVICE=backend)
```

Deployment script: `./deploy.sh` (build → tag → push → pull on server → compose up)

### First-time Setup

```bash
# 1. Generate secrets
./setup-secrets.sh > .env

# 2. Edit .env (set domain, bot token, OpenAI key, etc.)

# 3. Start
docker compose up -d

# 4. Check health
curl http://localhost:8080/health

# 5. Check dashboard
# Navigate to https://yourdomain.com/<ADMIN_PATH>/dashboard/admin
```

---

## 11. File Reference

### Backend (`backend/app/`)

| File | Key Code | Description |
|---|---|---|
| `main.py` | `create_app()`, `lifespan()` | FastAPI app factory; connects all services on startup |
| `core/config.py` | `Settings(BaseSettings)` | All env vars with Pydantic validation; enforces JWT_SECRET length in prod |
| `core/ratelimit.py` | `check_rate_limit()` | Sliding-window Redis rate limiter |
| `core/observability.py` | `setup_observability()` | Loguru + OpenTelemetry + Sentry setup |
| `core/activity.py` | `log_error_async()` | Async error logging to MongoDB |
| `auth/models.py` | `AuthUser`, `ChatMessage`, `BroadcastJob` | All auth DB models |
| `auth/router.py` | `/auth/telegram/login`, `/auth/refresh`, `/auth/me` | JWT auth endpoints |
| `auth/security.py` | `create_access_token()`, `validate_telegram_init_data()` | JWT creation, TG initData HMAC |
| `auth/dependencies.py` | `get_current_user()`, `require_permission()` | FastAPI auth dependencies |
| `auth/avatars.py` | `fetch_and_save_avatar()` | Download Telegram profile photo via Bot API |
| `scraper/scraper.py` | `NCFUScraper.run()`, `_flush_lessons_smart()` | 5-phase scrape pipeline with diff-sync |
| `scraper/client.py` | `NCFUClient` | Async HTTP client for eCampus API endpoints |
| `scraper/parser.py` | `parse_institute()`, `parse_week()` | Raw JSON → domain model conversion |
| `scraper/campus_scraper.py` | `sync_campuses()` | Campus/building data from NCFU public API |
| `ecampus/client.py` | `ECampusClient` | Browser-like client with captcha solving and HTML parsing |
| `ecampus/sync_service.py` | `ECampusSyncRecord`, `sync_all_users()` | Per-user eCampus data sync + AES encryption |
| `ecampus/queue.py` | `AsyncQueue`, `get_queue()` | In-memory async task queue with worker |
| `ecampus/router.py` | `/api/ecampus/*` | eCampus credentials, sync status, data endpoints |
| `graphql/schema.py` | `Query`, `Mutation`, `Subscription` | Strawberry schema with depth + token limiters |
| `graphql/resolvers.py` | `resolve_group_schedule()`, `resolve_free_rooms()` | MongoDB query resolvers |
| `graphql/types.py` | `GroupType`, `LessonConnection`, `DayType` | Strawberry GraphQL types |
| `scheduler/scheduler.py` | `setup_scheduler()`, `_run_scrape()` | APScheduler configuration |
| `models/group.py` | `Group`, `DaySchedule` | Group + embedded schedule model |
| `models/lesson.py` | `Lesson` | Individual lesson model |
| `models/teacher.py` | `Teacher` | Teacher with derived short name |
| `search/service.py` | `search_all()` | MongoDB regex search across groups/teachers/rooms |
| `cache/redis.py` | `init_redis()`, `get_redis()`, `invalidate_pattern()` | Redis connection + cache invalidation |

### Bot (`ecampus_bot/app/`)

| File | Key Code | Description |
|---|---|---|
| `main.py` | `create_app()`, telegram_webhook | FastAPI wrapper; HMAC webhook verification |
| `bot/__init__.py` | `setup_bot()`, `get_bot()`, `get_dp()` | aiogram bot and dispatcher initialization |
| `bot/handlers/ai_handler.py` | `handle_message()`, `extract_intent()`, `_dispatch()` | Main AI pipeline |
| `bot/handlers/commands.py` | `cmd_roles()`, `cmd_support()`, `cmd_suggest()`, `cmd_limit()` | Command handlers |
| `bot/handlers/extra_handlers.py` | `/me`, `/teacher`, `/classmates` | Profile-based schedule shortcuts |
| `bot/handlers/grades.py` | Grade-related command handling | eCampus grades via bot |
| `bot/handlers/bot_login.py` | `/login` command | Generate one-time login code for web |
| `bot/intents.py` | `IntentResponse`, all Intent classes | Pydantic models for OpenAI structured extraction |
| `bot/conversation.py` | `get_history()`, `add_message()` | Per-user context window in Redis/MongoDB |
| `bot/message_store.py` | `store_message()`, `store_bot_reply()` | Persist every exchange to MongoDB |
| `bot/middlewares/anti_flood.py` | `get_quota_status()`, quota enforcement | Per-user/chat AI request quota |
| `bot/middlewares/webhook_ratelimit.py` | Webhook-level rate limiting | Prevents webhook flooding |

### Web (`web/`)

| File | Key Code | Description |
|---|---|---|
| `app/layout.tsx` | Root layout | HTML shell, metadata, Providers wrapper |
| `app/schedule/page.tsx` | `SchedulePageInner` | Full schedule view with gestures, offline cache, live clock |
| `app/ecampus/page.tsx` | eCampus grades page | Personal grade display with sync management |
| `app/map/page.tsx` | Free rooms map | Campus building/room availability |
| `app/profile/page.tsx` | Profile settings | Role, group/teacher binding, UI preferences |
| `lib/store.ts` | `useScheduleStore` | Zustand store: search state, profile, auth, favorites |
| `lib/api.ts` | `api.*` | REST API client with anon and authed variants |
| `lib/auth.ts` | `initTelegramAuth()`, `getToken()` | Telegram WebApp initData login, JWT management |
| `lib/types.ts` | `Lesson`, `GroupMeta`, `WeekResponse` | TypeScript interfaces for all API data |
| `hooks/useGestures.ts` | `useGestures()` | Touch event detection (swipe + edge swipe) |
| `components/schedule/LessonCard.tsx` | `LessonCard` | Individual lesson UI with type icons and colors |
| `components/schedule/DayPicker.tsx` | `DayPicker` | Horizontal scrollable day selector |
| `components/schedule/SearchDropdown.tsx` | `SearchDropdown` | Live search results with keyboard navigation |
| `components/schedule/TeacherDashboard.tsx` | `TeacherDashboard` | Teacher stats panel (today's rooms, subjects) |
| `components/ecampus/ECampusSection.tsx` | `ECampusSection` | Grade display per subject |
| `components/ecampus/ProfileModals.tsx` | Login/link modals | eCampus account connection UI |
| `components/layout/MobileNav.tsx` | Bottom nav bar | Icon + label tabs for mobile |
| `components/layout/DesktopSidebar.tsx` | Left sidebar | Navigation for desktop (≥1024px) |
| `styles/globals.css` | CSS custom properties | Dark theme tokens (`--card`, `--cyan`, `--border`, etc.) |
| `public/manifest.json` | PWA manifest | App name, icons, display mode |
| `public/sww.js` | Service worker | Offline caching strategy |

### Infrastructure

| File | Description |
|---|---|
| `docker-compose.yml` | Production stack: mongo, redis, backend, bot, miniapp, dashboard, nginx, web |
| `docker-compose.dev.yml` | Development overrides (bind mounts, debug ports) |
| `docker-compose.staging.yml` | Staging configuration |
| `nginx/nginx.conf.template` | Nginx config with `${NGINX_ADMIN_PATH}` and `${NGINX_DOMAIN}` placeholders |
| `nginx/entrypoint.sh` | Substitutes env vars into nginx config template at container start |
| `docker/mongo/init.js` | MongoDB initialization: creates schedule and auth databases/users |
| `deploy.sh` | Full deployment script: build images, push to registry, pull on server, rolling restart |
| `setup-secrets.sh` | Generates all required secrets and writes them to `.env` |
| `Makefile` | Developer targets: `up`, `down`, `logs`, `scrape`, `build`, `shell`, `test` |
| `.github/workflows/deploy.yml` | CI/CD pipeline (push to main → deploy) |
| `.github/workflows/check.yml` | PR checks (lint, type check) |

---

*Generated on 2026-06-14. For the most current information, consult the source code directly.*
