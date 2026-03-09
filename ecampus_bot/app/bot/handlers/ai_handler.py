"""
Main AI handler.
1. Hash user message → check Redis cache
2. If miss: call Instructor/OpenAI to extract intent
3. Dispatch intent → call GraphQL backend
4. Format and send reply
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, date as _date
from typing import Optional

import instructor
import orjson
import httpx
from aiogram.types import Message
import asyncio as _aio

from loguru import logger
from openai import AsyncOpenAI

from app.cache.redis import get_redis
from app.bot.conversation import get_history, add_message, build_context_prompt
from app.bot.message_store import store_message, store_bot_reply
from app.core.config import settings
from app.bot.intents import (
    IntentResponse, TimeRef,
    GroupScheduleIntent, TeacherScheduleIntent,
    TeacherNowIntent, GroupNowIntent,
    FreeRoomsIntent, BuildingScheduleIntent, RoomScheduleIntent,
    SearchIntent, LessonsOnDayIntent,
    OverviewIntent, InstitutesIntent,
    UnknownIntent,
)

# GraphQL URL — points to the backend service.
# Overridden by BACKEND_GRAPHQL_URL env var (set in docker-compose).
from app.core.config import settings as _cfg
GRAPHQL_URL = _cfg.backend_graphql_url
CACHE_TTL   = 300
TG_MAX      = 4096   # Telegram hard limit per message

# ── Group name normalizer (tolerates spaces, dashes, latin, typos) ────────────

import re as _re

_LAT_TO_CYR_SINGLE = str.maketrans(
    "acehkmoptxyACEHKMOPTXY",   # Латиница (22 символа, без b/B)
    "асенкмортхуАСЕНКМОРТХУ"   # Кириллица (22 символа)
)
# 'b'/'B' handled separately since they map to 'б'/'Б' (not used in str.maketrans due to multi-char limitation)
_LAT_B_TABLE = str.maketrans("bB", "бБ")

_FORM_ALIAS = {
    "bak":"б","бак":"б","b":"б","бакалавр":"б",
    "mag":"м","маг":"м","m":"м","магистр":"м",
    "asp":"а","асп":"а","аспирант":"а",
    "spec":"с","спец":"с",
}
_BASE_ALIAS = {"очная":"о","очн":"о","заочная":"з","заоч":"з"}

def _normalize_group_for_query(raw: str | None) -> str | None:
    """
    Приводит любой вариант написания группы к виду, пригодному для поиска.
    'исс б о 22 3' / 'ISS-b-o-22-3' / 'аис25' / 'ИСС  Б О 22-3' → 'ИСС-б-о-22-3'
    Возвращает оригинал, если нормализация не дала результата.
    """
    if not raw:
        return raw
    s = raw.strip().lower()
    # Транслитерация
    try:
        from transliterate import translit
        if _re.search(r'[a-zA-Z]', s):
            s = translit(s, 'ru')
    except Exception:
        pass
    s = s.translate(_LAT_TO_CYR_SINGLE)
    s = s.translate(_LAT_B_TABLE)
    # Пробелы/дефисы/подчёркивания → дефис
    s = _re.sub(r'[\s\-_/\\]+', '-', s)
    s = _re.sub(r'[^\w\-]', '', s, flags=_re.UNICODE).strip('-')
    tokens = [t for t in s.split('-') if t]
    tokens = [_FORM_ALIAS.get(t, _BASE_ALIAS.get(t, t)) for t in tokens]
    # Сокращённые формы:
    # "исс222"  → "исс-б-о-22-2"    (3 цифры: год22 + подгруппа2)
    # "исс2224" → "исс-б-о-22-24"   (4 цифры: год22 + подгруппа24, редко)
    # "аис25"   → "аис-б-о-25"      (2 цифры: просто год)
    if len(tokens) == 1 and _re.match(r'^[а-яё]+\d{2,}$', tokens[0]):
        m = _re.match(r'^([а-яё]+)(\d{2})(\d+)?$', tokens[0])
        if m:
            tokens = [m.group(1), "б", "о", m.group(2)]
            if m.group(3): tokens.append(m.group(3))
    # "аис-25" → "аис-б-о-25"
    if len(tokens) == 2 and _re.match(r'^\d{2}$', tokens[-1]):
        tokens = [tokens[0], "б", "о", tokens[1]]
    result = '-'.join(tokens)
    # Вернуть в смешанном регистре как в оригинале если нормализация бессмысленна
    return result if len(result) >= 4 else raw

# ── Paged schedule — stores days in Redis, sends one day + nav buttons ────────

_PAGE_TTL = 3600   # 1 hour

async def _store_pages(key: str, pages: list[str]) -> None:
    import orjson
    r = get_redis()
    await r.setex(key, _PAGE_TTL, orjson.dumps(pages))

async def _load_pages(key: str) -> list[str] | None:
    import orjson
    r = get_redis()
    raw = await r.get(key)
    return orjson.loads(raw) if raw else None

def _page_key(user_id: int, tag: str) -> str:
    import hashlib
    h = hashlib.md5(tag.encode()).hexdigest()[:12]
    return f"bot:pages:{user_id}:{h}"

def _fmt_days_paged(days: list[dict], title: str,
                    show_teacher=True, show_group=False, show_institute=False) -> str:
    """
    Форматирует дни в виде ЕДИНОЙ строки с пагинацией.
    Первые 2 дня с парами — сразу, остальные — через кнопки листания.
    Если пар нет сегодня → показывает ближайший день с парами.
    Добавляет маркер PAGED:key:total в начало — handle_message его перехватит.
    """
    # Фильтруем дни с парами
    days_with = [d for d in days if d.get("lessons")]
    if not days_with:
        return _fmt_days(days, title, show_teacher, show_group, show_institute)

    today = _now_moscow().date().isoformat()
    today_day = next((d for d in days_with if d.get("date","")[:10] == today), None)
    if today_day and not today_day.get("lessons"):
        # Сегодня нет пар — ищем ближайший день
        future = [d for d in days_with if d.get("date","")[:10] > today]
        header = f"😴 Сегодня пар нет\n\n"
        if future:
            days_with = future   # покажем начиная с ближайшего дня
        else:
            return f"{header}📭 <b>{title}</b>\n\nБлижайших пар не найдено."

    # Возвращаем ПЕРВЫЙ день + маркер для пагинации
    # Фактическое сохранение в Redis и отправку с кнопками делает handle_message
    pages = [_fmt_days([d], title, show_teacher, show_group, show_institute) for d in days_with]
    if len(pages) == 1:
        return pages[0]
    # Маркер: handle_message распознает его и сохранит страницы
    import json as _json
    return f"\x00PAGED\x00{_json.dumps(pages)}\x00"

_MONTHS = ["","янв","фев","мар","апр","май","июн","июл","авг","сен","окт","ноя","дек"]
_WDAYS  = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
_WDAYS_FULL = ["понедельник","вторник","среда","четверг","пятница","суббота","воскресенье"]

_LT_SHORT = {
    "Лекция":                "Лек",
    "Практическое занятие":  "Пр",
    "Лабораторная работа":   "Лаб",
    "Семинар":               "Сем",
    "Консультация":          "Конс",
    "Зачёт":                 "Зач",
    "Экзамен":               "Экз",
}

# Official NCFU lesson schedule (start_time → pair number)
_NCFU_SLOTS: dict[str, int] = {
    "08:00": 1,
    "09:40": 2,
    "11:20": 3,
    "13:20": 4,
    "15:00": 5,
    "16:50": 6,
    "18:30": 7,
    "20:10": 8,
}

def _lesson_num(time_start: str) -> int:
    """Return official NCFU pair number by start time, or 0 if non-standard."""
    return _NCFU_SLOTS.get(time_start, 0)

# ── OpenAI / Instructor client ────────────────────────────────────────────────

_oai: Optional[instructor.AsyncInstructor] = None

def _get_instructor() -> instructor.AsyncInstructor:
    global _oai
    if _oai is None:
        apk = settings.openai_api_key.get_secret_value()
        _oai = instructor.from_openai(
            AsyncOpenAI(api_key=apk),
            mode=instructor.Mode.JSON,
        )
    return _oai


# ── Time helpers ──────────────────────────────────────────────────────────────

def _now_moscow() -> datetime:
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Moscow"))

def _resolve_time(time_ref) -> datetime:
    """Convert TimeRef (including date_expr and time_of_day) to a concrete datetime."""
    from zoneinfo import ZoneInfo
    tz  = ZoneInfo("Europe/Moscow")
    now = datetime.now(tz)

    if time_ref is None:
        return now

    # Exact ISO datetime
    if time_ref.iso:
        dt = datetime.fromisoformat(time_ref.iso)
        return dt.replace(tzinfo=tz) if dt.tzinfo is None else dt

    # Short relative offset in minutes (only when no date_expr)
    if time_ref.offset_minutes is not None and not time_ref.date_expr:
        return now + timedelta(minutes=time_ref.offset_minutes)

    # Named date expression
    target_date = None
    if time_ref.date_expr:
        expr = time_ref.date_expr.lower().strip()
        today = now.date()
        wd = today.weekday()   # 0=Mon … 6=Sun

        _WD = {
            "monday":0,"tuesday":1,"wednesday":2,"thursday":3,
            "friday":4,"saturday":5,"sunday":6,
        }

        if expr == "today":
            target_date = today
        elif expr == "tomorrow":
            target_date = today + timedelta(days=1)
        elif expr == "day_after_tomorrow":
            target_date = today + timedelta(days=2)
        elif expr == "next_week":
            target_date = today + timedelta(days=7 - wd)   # next Monday
        elif expr.startswith("next_"):
            twd = _WD.get(expr[5:])
            if twd is not None:
                target_date = today + timedelta(days=(twd - wd) % 7 or 7)
        elif expr in _WD:
            twd = _WD[expr]
            target_date = today + timedelta(days=(twd - wd) % 7 or 7)
        else:
            try:
                target_date = _date.fromisoformat(expr)
            except ValueError:
                pass

    if target_date is None:
        target_date = now.date()

    # Apply time_of_day or default to 08:00
    if getattr(time_ref, "time_of_day", None):
        try:
            h, m = map(int, time_ref.time_of_day.split(":"))
        except Exception:
            h, m = 8, 0
    else:
        h, m = 8, 0

    return datetime(target_date.year, target_date.month, target_date.day, h, m, tzinfo=tz)

def _fmt_date(iso: str) -> str:
    """'2026-03-04' → 'Ср, 4 мар'"""
    try:
        d = _date.fromisoformat(iso)
        return f"{_WDAYS[d.weekday()]}, {d.day} {_MONTHS[d.month]}"
    except Exception:
        return iso

async def _gql(query: str, variables: dict | None = None) -> dict:
    """Call backend GraphQL API over HTTP."""
    payload: dict = {"query": query}
    if variables:
        payload["variables"] = variables
    async with httpx.AsyncClient(timeout=15) as _client:
        resp = await _client.post(GRAPHQL_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
    if "errors" in data and data["errors"]:
        raise RuntimeError(str(data["errors"][0].get("message", data["errors"][0])))
    return data.get("data") or {}


# ── Intent extraction ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
СКФУ расписание. Сегодня {today} ({weekday}), {now} МСК. Завтра {tomorrow}, неделя {week}.
Извлеки intent из сообщения. Имена/группы/корпуса — дословно, как написал пользователь, БЕЗ изменений и расшифровок. Верни JSON {{result: <intent>}}."""

# TTLs for reply cache by intent type (seconds)
_REPLY_TTL: dict[str, int] = {
    "group_now":          60,    # changes every lesson slot
    "teacher_now":        60,
    "free_rooms":         120,
    "group_schedule":     600,
    "teacher_schedule":   600,
    "room_schedule":      600,
    "building_schedule":  300,
    "lessons_on_day":     300,
    "search":             300,
    "overview":           120,
    "institutes":         3600,
    "unknown":            0,     # never cache
}

def _intent_cache_key(intent) -> str | None:
    """Stable cache key based on intent type + parameters (not raw text)."""
    import json as _json
    d = intent.model_dump()
    d.pop("intent", None)
    # For now-type intents, bucket by 5-minute window so cache stays fresh
    intent_type = intent.intent
    if intent_type in ("group_now", "teacher_now", "free_rooms"):
        now = _now_moscow()
        bucket = now.strftime("%Y%m%d%H") + str(now.minute // 5)
        d["_bucket"] = bucket
    h = hashlib.md5(_json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]
    return f"bot:reply:{intent_type}:{h}"


async def extract_intent(text: str, history: list[dict] | None = None) -> IntentResponse:
    r = get_redis()
    # Intent cache — keyed by text + minute bucket (for "сейчас" queries)
    # Include a hash of last user message for context-aware caching
    now = _now_moscow()
    minute_bucket = now.strftime("%Y%m%d%H%M")
    ctx_hash = hashlib.md5(
        (history[-1]["content"] if history else "").encode()
    ).hexdigest()[:8] if history else "0"
    h = hashlib.md5(text.strip().lower().encode()).hexdigest()[:16]
    ck = f"bot:intent:{h}:{minute_bucket}:{ctx_hash}"

    cached = await r.get(ck)
    if cached:
        return IntentResponse.model_validate(orjson.loads(cached))

    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    context_str = build_context_prompt(history or [])
    system = SYSTEM_PROMPT.format(
        today=now.date().isoformat(),
        weekday=_WDAYS_FULL[now.weekday()],
        now=now.strftime("%H:%M"),
        tomorrow=tomorrow,
        week=now.isocalendar().week,
    )
    if context_str:
        system = system + "\n\n" + context_str

    client = _get_instructor()
    try:
        response: IntentResponse = await client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=IntentResponse,
            max_retries=2, # Instructor сам делает ретраи, если схема не совпала
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": text},
            ],
        )
    except Exception as exc:
        logger.error(f"OpenAI API error in extract_intent: {exc}")
        raise

    try:
        await r.setex(ck, CACHE_TTL, orjson.dumps(response.model_dump()))
    except Exception as exc:
        logger.warning(f"intent cache write failed: {exc}")
    return response


# ── GraphQL templates ─────────────────────────────────────────────────────────

_GQL_GROUP_SCHEDULE = """
query($gn: String, $gid: Int, $from: String, $to: String, $week: Int) {
  groupSchedule(groupName: $gn, groupId: $gid, fromDate: $from, toDate: $to, week: $week) {
    date weekdayName weekNumber
    lessons { timeStart timeEnd subject lessonType teacherName roomName building subgroup instituteName }
  }
}"""

_GQL_TEACHER_SCHEDULE = """
query($tn: String, $tid: Int, $from: String, $to: String, $week: Int) {
  teacherSchedule(teacherName: $tn, teacherId: $tid, fromDate: $from, toDate: $to, week: $week) {
    date weekdayName weekNumber
    lessons { timeStart timeEnd subject lessonType groupName teacherName roomName building instituteName }
  }
}"""

_GQL_ROOM_SCHEDULE = """
query($rn: String, $rid: Int, $from: String, $to: String) {
  roomSchedule(roomName: $rn, roomId: $rid, fromDate: $from, toDate: $to) {
    date weekdayName
    lessons { timeStart timeEnd subject groupName teacherName instituteName }
  }
}"""

_GQL_FREE_ROOMS = """
query($at: String!, $dur: Int!, $b: String) {
  freeRooms(at: $at, duration: $dur, building: $b) {
    roomId name building capacity
  }
}"""

_GQL_SEARCH = """
query($q: String!) {
  search(q: $q) {
    groups   { groupId name instituteName course }
    teachers { teacherId fullName shortName subjects }
    rooms    { roomId name building }
    dataAsOf
  }
}"""

_GQL_LESSONS_DAY = """
query($day: String!, $gid: Int, $gn: String, $tn: String, $rn: String, $iname: String) {
  lessonsOn(date: $day, groupId: $gid, groupName: $gn, teacherName: $tn, roomName: $rn,
               instituteName: $iname, first: 50) {
    nodes { timeStart timeEnd subject lessonType groupName teacherName roomName building instituteName }
    pageInfo { totalCount }
  }
}"""

_GQL_OVERVIEW = """
query {
  overview {
    groupsTotal teachersTotal roomsTotal lessonsTotal institutesTotal
    lastScrapeAt lastScrapeStatus lastScrapeMode lastScrapeDuration lessonsWrittenLast
    upcomingDays { date weekdayName lessonsCount groupsActive }
    topSubjects  { subject lessonsCount groupsCount }
  }
}"""

_GQL_INSTITUTES = """
query($q: String) {
  institutes(q: $q) {
    instituteId shortName name branchId groupsCount
  }
}"""


# ── Formatters ────────────────────────────────────────────────────────────────

def _lesson_lines(l: dict, show_teacher=True, show_group=False,
                  num: int = 0, show_institute=False) -> list[str]:
    """Render one lesson as 2-3 tidy lines with correct NCFU pair number."""
    lt = _LT_SHORT.get(l.get("lessonType",""), l.get("lessonType",""))
    lt_str = f"  <i>{lt}</i>" if lt else ""

    # Pair number: use official NCFU slot table, fall back to positional index
    slot_num = _lesson_num(l.get("timeStart", ""))
    actual_num = slot_num if slot_num else num
    num_str = f"<b>{actual_num} пара</b>  " if actual_num else ""

    # Line 1: number + time + subject
    lines = [f"{num_str}🕐 <b>{l['timeStart']}–{l['timeEnd']}</b>  {l['subject']}{lt_str}"]

    # Line 2: room
    room = l.get("roomName","").strip()
    if room:
        lines.append(f"    🚪 {room}")

    # Line 3: teacher or group (depending on context)
    if show_teacher and l.get("teacherName"):
        lines.append(f"    👤 {l['teacherName']}")
    if show_group and l.get("groupName"):
        lines.append(f"    👥 {l['groupName']}")

    # Line 4: institute (when requested)
    if show_institute and l.get("instituteName"):
        lines.append(f"    🏛 {l['instituteName']}")

    return lines


def _fmt_days(days: list[dict], title: str,
              show_teacher=True, show_group=False, show_institute=False) -> str:
    if not days:
        return f"📭 <b>{title}</b>\n\nРасписание не найдено."

    chunks = [f"📅 <b>{title}</b>"]

    for day in days:
        lessons = day.get("lessons", [])
        if not lessons:
            continue

        date_label = _fmt_date(day.get("date",""))
        week = day.get("weekNumber","")
        week_str = f"  •  {week} нед." if week else ""
        chunks.append(f"\n<b>── {date_label}{week_str} ──</b>")

        for i, l in enumerate(lessons):
            if i > 0:
                chunks.append("")          # blank separator between lessons
            chunks.extend(_lesson_lines(
                l,
                show_teacher=show_teacher,
                show_group=show_group,
                num=i+1,           # positional fallback only
                show_institute=show_institute,
            ))

    return "\n".join(chunks)


def _fmt_now(name: str, at_time: str, active: list, upcoming: list,
             show_teacher=True, show_group=False) -> str:
    if active:
        lines = [f"📍 <b>{name}</b>  сейчас ({at_time})\n"]
        for l in active:
            lines.extend(_lesson_lines(l, show_teacher=show_teacher, show_group=show_group))
        return "\n".join(lines)
    if upcoming:
        l = upcoming[0]
        room = f"ауд. {l['roomName']}" if l.get("roomName") else "—"
        extra = l.get("groupName") or l.get("teacherName") or ""
        extra_str = f"\n    👥 {extra}" if extra else ""
        return (
            f"💤 <b>{name}</b>  сейчас нет пары\n\n"
                f"Следующая в <b>{l['timeStart']}</b>\n"
                f"📖 {l['subject']}\n"
                f"🚪 {room}{extra_str}"
        )
    return f"🏁 У <b>{name}</b> сегодня больше нет пар."


def _fmt_free_rooms(rooms: list[dict], at: datetime, building: str | None) -> str:
    at_str = at.strftime("%H:%M")
    today  = _now_moscow().date()
    if at.date() != today:
        date_label = f"{_fmt_date(at.date().isoformat())}, {at_str}"
    else:
        date_label = at_str
    loc = f" · {building}" if building else ""
    if not rooms:
        return f"🚫 Свободных аудиторий{loc} на <b>{date_label}</b> не найдено."

    by_b: dict[str, list] = {}
    for r in rooms:
        by_b.setdefault(r.get("building") or "—", []).append(r)

    total = len(rooms)
    lines = [f"🟢 <b>Свободные аудитории на {date_label}{loc}</b>  <i>({total} всего)</i>\n"]
    for b_name in sorted(by_b):
        b_rooms = by_b[b_name]
        lines.append(f"<b>{b_name}</b>  <i>({len(b_rooms)})</i>")
        for r in b_rooms[:15]:
            cap = f"  <i>({r['capacity']} мест)</i>" if r.get("capacity") else ""
            lines.append(f"  • {r['name']}{cap}")
        if len(b_rooms) > 15:
            lines.append(f"  <i>... и ещё {len(b_rooms) - 15}</i>")
    return "\n".join(lines)


def _fmt_search(data: dict, query: str) -> str:
    groups   = data.get("groups", [])
    teachers = data.get("teachers", [])
    rooms    = data.get("rooms", [])
    if not groups and not teachers and not rooms:
        return f"🔍 По запросу «<b>{query}</b>» ничего не найдено."

    lines = [f"🔍 <b>«{query}»</b>"]
    if groups:
        lines.append("\n<b>Группы</b>")
        for g in groups[:8]:
            course = f", {g['course']} курс" if g.get("course") else ""
            inst = g.get("instituteName","")
            lines.append(f"  • <b>{g['name']}</b>  <i>{inst}{course}</i>")
    if teachers:
        lines.append("\n<b>Преподаватели</b>")
        for t in teachers[:8]:
            subj = ", ".join((t.get("subjects") or [])[:2])
            lines.append(f"  • <b>{t['fullName']}</b>" + (f"  <i>{subj}</i>" if subj else ""))
    if rooms:
        lines.append("\n<b>Аудитории</b>")
        for r in rooms[:8]:
            b = f"  <i>{r['building']}</i>" if r.get("building") else ""
            lines.append(f"  • <b>{r['name']}</b>{b}")
    return "\n".join(lines)


def _fmt_overview(ov: dict) -> str:
    status_icon = "✅" if ov.get("lastScrapeStatus") == "success" else "⚠️"
    lines = [
        "📊 <b>СКФУ · Расписание</b>\n",
        f"👥 Групп:            <b>{ov['groupsTotal']}</b>",
        f"👨‍🏫 Преподавателей:  <b>{ov['teachersTotal']}</b>",
        f"🚪 Аудиторий:        <b>{ov['roomsTotal']}</b>",
        f"📚 Занятий в базе:   <b>{ov['lessonsTotal']}</b>",
        f"🏛 Подразделений:    <b>{ov['institutesTotal']}</b>",
    ]
    if ov.get("lastScrapeAt"):
        dur = f", {ov['lastScrapeDuration']:.0f}с" if ov.get("lastScrapeDuration") else ""
        lines.append(
            f"\n{status_icon} Обновлено: "
                f"{ov['lastScrapeAt'][:16].replace('T',' ')} "
                f"({ov.get('lastScrapeMode','?')}{dur})"
        )
    upcoming = ov.get("upcomingDays", [])
    if upcoming:
        lines.append("\n<b>📆 Ближайшие дни</b>")
        for d in upcoming[:5]:
            bar = "▪" * min(10, d['lessonsCount'] // 5)
            lines.append(
                f"  {d['weekdayName'][:2]} {d['date'][5:]}  "
                    f"{bar}  {d['lessonsCount']} пар · {d['groupsActive']} групп"
            )
    top = ov.get("topSubjects", [])
    if top:
        lines.append("\n<b>📖 Топ дисциплин</b>")
        for s in top[:5]:
            lines.append(f"  • {s['subject']}  <i>({s['lessonsCount']})</i>")
    return "\n".join(lines)


def _fmt_institutes(institutes: list[dict]) -> str:
    if not institutes:
        return "🏛 Институты не найдены."
    main   = [i for i in institutes if i.get("branchId", 1) == 1]
    branch = [i for i in institutes if i.get("branchId", 1) != 1]
    lines  = ["🏛 <b>Институты и факультеты СКФУ</b>\n"]
    for i in main:
        lines.append(f"  <b>{i['shortName']}</b> — {i['name']}  <i>({i['groupsCount']} гр.)</i>")
    if branch:
        lines.append("\n<b>Филиалы</b>")
        for i in branch:
            lines.append(f"  <b>{i['shortName']}</b> — {i['name']}  <i>({i['groupsCount']} гр.)</i>")
    return "\n".join(lines)


def _split_chunks(text: str) -> list[str]:
    """Split text into Telegram-safe ≤4096-char chunks on paragraph boundaries."""
    if len(text) <= TG_MAX:
        return [text]
    chunks = []
    chunk = ""
    for para in text.split("\n\n"):
        candidate = (chunk + "\n\n" + para).lstrip("\n") if chunk else para
        if len(candidate) <= TG_MAX:
            chunk = candidate
        else:
            if chunk:
                chunks.append(chunk)
            if len(para) > TG_MAX:
                # paragraph too long — split on single newlines
                sub = ""
                for line in para.split("\n"):
                    cand = (sub + "\n" + line).lstrip("\n") if sub else line
                    if len(cand) <= TG_MAX:
                        sub = cand
                    else:
                        if sub:
                            chunks.append(sub)
                        sub = line[:TG_MAX]
                chunk = sub
            else:
                chunk = para
    if chunk:
        chunks.append(chunk)
    return chunks


# ── Building schedule helper ──────────────────────────────────────────────────

_GQL_ROOM_SCHEDULE_TODAY = """
query($rn: String, $from: String, $to: String) {
  roomSchedule(roomName: $rn, fromDate: $from, toDate: $to) {
    date
    lessons { timeStart timeEnd subject groupName teacherName roomName }
  }
}"""

_GQL_ROOM_SEARCH_BY_NUM = """
query($q: String, $b: String) {
  rooms(q: $q, first: 20) {
    nodes { roomId name building }
  }
}"""

_GQL_ROOMS_IN_BUILDING = """
query($q: String) {
  rooms(q: $q, first: 200) {
    nodes { roomId name building }
  }
}"""


def _normalize_building(b: str) -> str:
    """'11 корпус' / 'корпус 11' / '11' → just the identifier part for regex matching."""
    return _re.sub(r'(?i)корпус\s*', '', b).strip()


async def _dispatch_building_schedule(building: str, target_date: _date | None = None) -> str:
    """Show today's (or any day's) time slots when rooms are free in a given building."""
    num = _normalize_building(building)
    if target_date is None:
        target_date = _now_moscow().date()
    today = target_date.isoformat()
    now_time = _now_moscow().strftime("%H:%M") if target_date == _now_moscow().date() else "99:99"
    data = await _gql(_GQL_ROOMS_IN_BUILDING, {"q": num})
    all_rooms = data.get("rooms", {}).get("nodes", [])
    # filter to only rooms whose building contains the number
    rooms = [r for r in all_rooms
        if r.get("building") and _re.search(num, r["building"], _re.IGNORECASE)]

    if not rooms:
        return f"🏢 Корпус <b>{building}</b>: аудитории не найдены в базе."

    # 2. For each room fetch today's lessons — collect busy intervals
    busy: dict[str, list[tuple[str, str]]] = {}
    for r in rooms:
        gql_data = await _gql(_GQL_ROOM_SCHEDULE_TODAY, {
            "rn": r["name"], "from": today, "to": today,
        })
        days = gql_data.get("roomSchedule", [])
        intervals = []
        for day in days:
            for l in day.get("lessons", []):
                intervals.append((l["timeStart"], l["timeEnd"]))
        busy[r["name"]] = sorted(intervals)

    # 3. Build free-window summary per room, then aggregate by time slot
    # Standard NCFU lesson slots
    SLOTS = [
        ("08:00", "09:30"),
        ("09:40", "11:10"),
        ("11:20", "12:50"),
        ("13:20", "14:50"),
        ("15:00", "16:30"),
        ("16:40", "18:10"),
        ("18:20", "19:50"),
    ]

    # For each slot, collect rooms that are free the whole slot
    free_by_slot: dict[tuple, list[str]] = {s: [] for s in SLOTS}
    for r in rooms:
        intervals = busy[r["name"]]
        for slot in SLOTS:
            s_start, s_end = slot
            occupied = any(bs < s_end and be > s_start for bs, be in intervals)
            if not occupied:
                free_by_slot[slot].append(r["name"])

    # 4. Format
    b_label = f"Корпус {num}" if num.isdigit() else building
    date_label = _fmt_date(target_date.isoformat())
    lines = [f"🏢 <b>{b_label}</b> · {date_label} · свободные аудитории\n"]
    any_found = False
    for (s_start, s_end), room_names in free_by_slot.items():
        if not room_names:
            continue
        any_found = True
        past = s_end <= now_time
        icon = "⬜" if past else "🟢"
        lines.append(f"{icon} <b>{s_start}–{s_end}</b>  ({len(room_names)} св.)")
        shown = room_names[:8]
        lines.append("    " + "  ".join(shown) + ("  …" if len(room_names) > 8 else ""))

    if not any_found:
        lines.append("Все аудитории заняты весь день.")

    return "\n".join(lines)


# ── Disambiguation helpers ─────────────────────────────────────────────────────

# Sentinel prefix that handle_message checks to enter disambiguation flow
_DISAMBIG_SENTINEL = "__DISAMBIG__"

_DISAMBIG_TTL = 600  # 10 minutes in Redis
_DISAMBIG_PAGE_SIZE = 5  # max candidates per page in disambiguation keyboard


def _canonical_group_name(days: list[dict]) -> str | None:
    """Extract the real group name stored in DB from the first lesson of the schedule."""
    for day in days:
        for lesson in (day.get("lessons") or []):
            name = lesson.get("groupName") or lesson.get("group_name")
            if name:
                return name
    return None


def _score_group_candidate(name: str, query_core: str) -> int:
    """
    Score a group candidate against the normalized query.
    Penalizes branch-campus groups that have a short prefix (п-исп-222, е-исс-22).
    Main campus groups like исс-б-о-22-2 get no penalty.
    """
    import re as _r2
    try:
        from rapidfuzz import fuzz as fzf
        base = fzf.WRatio(query_core, _r2.sub(r"[\s\-_]", "", name.lower()))
    except ImportError:
        base = 50
    # Detect branch prefix: single/double-letter followed by dash at start of name
    # e.g. "п-исп-222", "е-исс-22-3" — query "исс" has NO such prefix
    branch_m = _r2.match(r"^([а-яёa-z]{1,2})-", name.lower())
    if branch_m:
        prefix = branch_m.group(1)
        if not query_core.startswith(prefix + "-") and not query_core.startswith(prefix):
            base -= 40  # Heavy penalty: this is a branch group, not what user wants
    return base


async def _find_group_candidates(group_name: str) -> list[dict]:
    """
    Return a list of group dicts that match `group_name` via GraphQL search.
    Returns 1 item if the match is unambiguous, >1 for disambiguation.
    Branch-campus groups (п-исп-222, е-исс-22) are penalized heavily so that
    main-campus groups (исс-б-о-22-2) rank first.
    """
    import re as _r
    data = await _gql(_GQL_SEARCH, {"q": group_name})
    candidates = data.get("search", {}).get("groups", [])
    if not candidates:
        return []

    # Normalized core of query (no separators, lowercase)
    core = _r.sub(r"[\s\-_]", "", group_name.lower())

    try:
        from rapidfuzz import process as fz, fuzz as fzf
        # Score ALL candidates with branch penalty, then sort
        scored = []
        for c in candidates:
            name_core = _r.sub(r"[\s\-_]", "", c["name"].lower())
            score = _score_group_candidate(c["name"], core)
            scored.append((c, name_core, score))
        scored.sort(key=lambda x: -x[2])

        good = [(c, name_core, score) for c, name_core, score in scored if score >= 15]
        if not good:
            # fallback: return top scored regardless
            good = scored[:8]

        # If top result is clearly best (gap >= 20 points AND score > 60) — return it alone
        if (len(good) >= 2
            and good[0][2] - good[1][2] >= 20
                and good[0][2] >= 60):
            best = good[0][0]
            return [{"group_id": best["groupId"], "name": best["name"],
                     "institute_name": best.get("instituteName") or "",
                     "course": best.get("course")}]

        return [{"group_id": c["groupId"], "name": c["name"],
                 "institute_name": c.get("instituteName") or "",
                 "course": c.get("course")}
            for c, _, _ in good[:8]]
    except ImportError:
        best = candidates[0]
        return [{"group_id": best["groupId"], "name": best["name"],
                 "institute_name": best.get("instituteName") or "",
                 "course": best.get("course")}]


async def _find_room_candidates(room_name: str) -> list[dict]:
    """
    Parse room name and find matching rooms via GraphQL.
    Handles: "11-405", "405", "спортзал", "9-с/з", "с/з" etc.
    """
    import re as _r

    rn       = room_name.strip()
    rn_lower = rn.lower()

    # ── Gym detection ────────────────────────────────────────────────────────
    _GYM_RE = _r.compile(
        r'(?:спортивный\s*зал|спортзал|спорт\s*зал|с/з|с\.з\.?|^сз$|gym)',
        _r.IGNORECASE,
    )
    _GYM_WITH_BLDG_RE = _r.compile(
        r'(?:корпус\s*)?(\d{1,2})\s*[-–\s]\s*(?:спортивный\s*зал|спортзал|спорт\s*зал|с/з|с\.з\.?|сз|gym)',
        _r.IGNORECASE,
    )
    bldg_gym = _GYM_WITH_BLDG_RE.match(rn)
    is_gym   = bool(bldg_gym) or bool(_GYM_RE.search(rn_lower))

    # ── Building-room pattern: "11-405", "11 405" ────────────────────────────
    m = _r.match(r'^(\d{1,2})[- ](\d{3,})$', rn)
    bldg = m.group(1) if m else (bldg_gym.group(1) if bldg_gym else None)
    rnum = m.group(2) if m else None

    # Build search query
    if is_gym:
        q = f"{bldg} спортзал" if bldg else "спортзал"
    elif rnum:
        q = f"{bldg}-{rnum}" if bldg else rnum
    else:
        q = rn

    data  = await _gql(_GQL_ROOM_SEARCH_BY_NUM, {"q": q})
    rooms = data.get("rooms", {}).get("nodes", [])

    # If building specified — filter results to that building
    if bldg and rooms:
        filtered = [r for r in rooms
            if r.get("building") and _r.search(_r.escape(bldg), r["building"], _r.IGNORECASE)
            or r.get("name", "").startswith(f"{bldg}-")]
        if filtered:
            rooms = filtered

    if not rooms:
        # Broader fallback
        data2 = await _gql(_GQL_SEARCH, {"q": q})
        rooms = data2.get("search", {}).get("rooms", [])
        rooms = [{"roomId": r["roomId"], "name": r["name"], "building": r.get("building", "")}
            for r in rooms]
    else:
        rooms = [{"roomId": r["roomId"], "name": r["name"], "building": r.get("building", "")}
            for r in rooms]

    return [{"room_id": r["roomId"], "name": r["name"], "building": r.get("building") or ""}
        for r in rooms[:10]]


def _pack_disambig(candidates: list[dict], intent_type: str, extra_params: dict) -> str:
    """Serialise disambiguation state for Redis storage. Returns the Redis key suffix."""
    import json as _json
    import hashlib, time
    payload = _json.dumps({
        "candidates": candidates,
        "intent_type": intent_type,
        "params": extra_params,
        "ts": int(time.time()),
    }, ensure_ascii=False)
    return payload


async def _store_disambig(user_id: int, payload: str) -> str:
    """Store disambiguation payload in Redis, return the key."""
    import hashlib
    key = f"disambig:{user_id}:{hashlib.md5(payload.encode()).hexdigest()[:10]}"
    r = get_redis()
    await r.setex(key, _DISAMBIG_TTL, payload.encode())
    return key


async def _load_disambig(key: str) -> dict | None:
    import json as _json
    r = get_redis()
    raw = await r.get(key)
    return _json.loads(raw) if raw else None


# ── Main handler ──────────────────────────────────────────────────────────────

def _make_nav_kb(page_key: str, idx: int, total: int):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    if idx > 0:
        buttons.append(InlineKeyboardButton(text="◀ Пред.", callback_data=f"pg:{page_key}:{idx-1}:{total}"))
    buttons.append(InlineKeyboardButton(text=f"{idx+1}/{total}", callback_data="pg_noop"))
    if idx < total - 1:
        buttons.append(InlineKeyboardButton(text="След. ▶", callback_data=f"pg:{page_key}:{idx+1}:{total}"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def _add_feedback_row(
    kb,          # existing InlineKeyboardMarkup | None
    chat_id: int,
    message_id: int,
) -> "InlineKeyboardMarkup":
    """
    Append a 👍 / 👎 feedback row to an existing keyboard (or create one).
    callback_data: "fb:{rating}:{chat_id}:{message_id}"
    """
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    fb_row = [
        InlineKeyboardButton(text="👍", callback_data=f"fb:like:{chat_id}:{message_id}"),
        InlineKeyboardButton(text="👎", callback_data=f"fb:dislike:{chat_id}:{message_id}"),
    ]
    existing_rows = kb.inline_keyboard if kb else []
    return InlineKeyboardMarkup(inline_keyboard=list(existing_rows) + [fb_row])


async def _store_feedback_meta(
    chat_id: int,
    message_id: int,
    user_text: str,
    bot_text: str,
) -> None:
    """
    Pre-create or update BotFeedback doc with the message content so that
    when a user later rates the message the text is already there.
    """
    try:
        from app.auth.models import BotFeedback
        from datetime import datetime
        existing = await BotFeedback.find_one(
            BotFeedback.chat_id == chat_id,
            BotFeedback.message_id == message_id,
        )
        if existing is None:
            doc = BotFeedback(
                chat_id=chat_id,
                message_id=message_id,
                tg_id=0,           # will be filled when user rates
                user_text=user_text[:1000],
                bot_text=bot_text[:2000],
                rating=None,
                updated_at=datetime.utcnow(),
            )
            await doc.insert()
        else:
            existing.user_text = user_text[:1000]
            existing.bot_text  = bot_text[:2000]
            await existing.save()
    except Exception as exc:
        logger.warning(f"_store_feedback_meta failed: {exc}")


async def _upsert_user(tg_user) -> None:
    """
    Create or update AuthUser from a Telegram user object.
    Called fire-and-forget on every incoming message so that users who never
    run /start still get a proper display name in the dashboard.
    Always refreshes first_name / last_name / username in case they changed.
    """
    try:
        from app.auth.models import AuthUser
        from datetime import datetime
        user = await AuthUser.find_one(AuthUser.tg_id == tg_user.id)
        if user is None:
            user = AuthUser(
                tg_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name or "",
                last_name=tg_user.last_name,
            )
            await user.insert()
        else:
            # Always refresh name fields — user may have changed them in Telegram
            user.first_name  = tg_user.first_name or user.first_name or ""
            user.last_name   = tg_user.last_name  or user.last_name
            user.username    = tg_user.username    or user.username
            user.last_active = datetime.utcnow()
            await user.save()
    except Exception as exc:
        logger.warning(f"_upsert_user failed tg_id={tg_user.id}: {exc}")


async def handle_message(message: Message) -> Message | None:


    # ── Dispatch ──────────────────────────────────────────────────────────────────

    async def _dispatch(intent) -> str:
        if isinstance(intent, GroupScheduleIntent):
            # Normalize group name to handle "исс222", "ИСС б о 22 3", "ISS-b-o-22-3" etc.
            group_name = _normalize_group_for_query(intent.group_name) if intent.group_name else None
            # Default: from today forward (not the whole week including past days)
            from_date = intent.from_date or _now_moscow().date().isoformat()
            to_date   = intent.to_date

            # ── Disambiguation: check for multiple matching groups BEFORE GQL ──
            resolved_group_id = intent.group_id
            resolved_group_name = group_name
            if group_name and not intent.group_id:
                candidates = await _find_group_candidates(group_name)
                if len(candidates) > 1:
                    return _DISAMBIG_SENTINEL + _pack_disambig(
                        candidates, "group_schedule",
                        {"from": from_date, "to": to_date, "week": intent.week},
                    )
                elif len(candidates) == 1:
                    # Use DB canonical name to display correctly
                    resolved_group_name = candidates[0]["name"]
                    resolved_group_id   = candidates[0]["group_id"]

            data = await _gql(_GQL_GROUP_SCHEDULE, {
                "gn": resolved_group_name, "gid": resolved_group_id,
                "from": from_date, "to": to_date, "week": intent.week,
            })
            days  = data.get("groupSchedule", [])
            canonical = resolved_group_name or f"группа #{resolved_group_id}"
            # Institute name from first lesson (all lessons of same group share it)
            inst_name = ""
            for day in days:
                for lesson in day.get("lessons", []):
                    if lesson.get("instituteName"):
                        inst_name = lesson["instituteName"]
                        break
                if inst_name:
                    break
            title = f"Расписание · {canonical}"
            if inst_name:
                title += f"\n🏛 {inst_name}"
            return _fmt_days_paged(days, title,
                                   show_teacher=True, show_group=False)

        if isinstance(intent, TeacherScheduleIntent):
            from_date = intent.from_date or _now_moscow().date().isoformat()
            data = await _gql(_GQL_TEACHER_SCHEDULE, {
                "tn": intent.teacher_name, "tid": None,
                "from": from_date, "to": intent.to_date, "week": intent.week,
            })
            days = data.get("teacherSchedule", [])
            # Extract full name and institute from first available lesson
            full_teacher_name = intent.teacher_name
            inst_name = ""
            for day in days:
                for lesson in day.get("lessons", []):
                    if lesson.get("teacherName"):
                        full_teacher_name = lesson["teacherName"]
                    if lesson.get("instituteName"):
                        inst_name = lesson["instituteName"]
                    break  # first lesson is enough
                if full_teacher_name != intent.teacher_name:
                    break
            title = f"Расписание · {full_teacher_name}"
            if inst_name:
                title += f"\n🏛 {inst_name}"
            return _fmt_days_paged(days, title,
                                   show_teacher=False, show_group=True)

        if isinstance(intent, TeacherNowIntent):
            at = _resolve_time(intent.time_ref)
            day = at.date().isoformat()
            data = await _gql(_GQL_LESSONS_DAY, {
                "day": day, "tn": intent.teacher_name,
                "gn": None, "rn": None, "iname": None,
            })
            nodes    = data.get("lessonsOn", {}).get("nodes", [])
            at_time  = at.strftime("%H:%M")
            active   = [l for l in nodes if l["timeStart"] <= at_time <= l["timeEnd"]]
            upcoming = [l for l in nodes if l["timeStart"] > at_time]
            return _fmt_now(intent.teacher_name, at_time, active, upcoming,
                            show_teacher=False, show_group=True)

        if isinstance(intent, GroupNowIntent):
            at = _resolve_time(intent.time_ref)
            day = at.date().isoformat()
            group_name = _normalize_group_for_query(intent.group_name)
            if not group_name:
                return "ERROR: группа не найдена"
            # Disambiguation
            candidates = await _find_group_candidates(group_name)
            if len(candidates) > 1:
                return _DISAMBIG_SENTINEL + _pack_disambig(
                    candidates, "group_now",
                    {"time_ref": intent.time_ref.model_dump() if intent.time_ref else None},
                )
            data = await _gql(_GQL_LESSONS_DAY, {
                "day": day, "gn": group_name,
                "tn": None, "rn": None, "iname": None,
            })
            nodes    = data.get("lessonsOn", {}).get("nodes", [])
            at_time  = at.strftime("%H:%M")
            active   = [l for l in nodes if l["timeStart"] <= at_time <= l["timeEnd"]]
            upcoming = [l for l in nodes if l["timeStart"] > at_time]
            # Canonical name from nodes
            canonical = (nodes[0].get("groupName") if nodes else None) or group_name
            return _fmt_now(canonical, at_time, active, upcoming,
                            show_teacher=True, show_group=False)

        if isinstance(intent, FreeRoomsIntent):
            at = _resolve_time(intent.time_ref)
            data = await _gql(_GQL_FREE_ROOMS, {
                "at": at.isoformat(), "dur": intent.duration_minutes, "b": intent.building,
            })
            return _fmt_free_rooms(data.get("freeRooms", []), at, intent.building)

        if isinstance(intent, BuildingScheduleIntent):
            target_dt = _resolve_time(intent.time_ref)
            return await _dispatch_building_schedule(intent.building, target_dt.date())

        if isinstance(intent, RoomScheduleIntent):
            from_date = intent.from_date or _now_moscow().date().isoformat()

            # ── Room disambiguation ───────────────────────────────────────────
            resolved_room_id   = intent.room_id
            resolved_room_name = intent.room_name

            if intent.room_name and not intent.room_id:
                room_candidates = await _find_room_candidates(intent.room_name)
                if len(room_candidates) == 0:
                    return f"🚫 Аудитория <b>{intent.room_name}</b> не найдена в базе."
                elif len(room_candidates) == 1:
                    resolved_room_id   = room_candidates[0]["room_id"]
                    resolved_room_name = room_candidates[0]["name"]
                else:
                    # Check if all found rooms are in the same building
                    buildings = list({c["building"] for c in room_candidates if c["building"]})
                    if len(buildings) == 1:
                        # Single building — pick first exact match by room number
                        resolved_room_id   = room_candidates[0]["room_id"]
                        resolved_room_name = room_candidates[0]["name"]
                    else:
                        # Multiple buildings — ask user to choose
                        return _DISAMBIG_SENTINEL + _pack_disambig(
                            [{"group_id": 0, "name": c["name"],
                              "institute_name": c["building"],
                              "room_id": c["room_id"],
                              "room_name": c["name"],
                              "building": c["building"]}
                                for c in room_candidates],
                            "room_schedule",
                            {"from": from_date, "to": intent.to_date,
                             "room_candidates": room_candidates},
                        )

            data = await _gql(_GQL_ROOM_SCHEDULE, {
                "rn": resolved_room_name, "rid": resolved_room_id,
                "from": from_date, "to": intent.to_date,
            })
            title = resolved_room_name or f"ауд. #{resolved_room_id}"
            days  = data.get("roomSchedule", [])
            return _fmt_days_paged(days, f"Расписание · {title}",
                                   show_teacher=True, show_group=True,
                                   show_institute=False)

        if isinstance(intent, SearchIntent):
            data = await _gql(_GQL_SEARCH, {"q": intent.query})
            search_data = data.get("search", {})

            # ── Auto-redirect: if exactly one teacher found and no groups/rooms ──
            teachers = search_data.get("teachers", [])
            groups   = search_data.get("groups", [])
            rooms    = search_data.get("rooms", [])
            if len(teachers) == 1 and not groups and not rooms:
                # Single teacher match — show their schedule directly
                teacher_name = teachers[0].get("fullName", intent.query)
                from_date = _now_moscow().date().isoformat()
                data2 = await _gql(_GQL_TEACHER_SCHEDULE, {
                    "tn": teacher_name, "tid": teachers[0].get("teacherId"),
                    "from": from_date, "to": None, "week": None,
                })
                days = data2.get("teacherSchedule", [])
                # Pick full name and institute from first lesson
                real_name = teacher_name
                inst2 = ""
                for day2 in days:
                    for les2 in day2.get("lessons", []):
                        real_name = les2.get("teacherName") or real_name
                        inst2 = les2.get("instituteName") or inst2
                        if real_name != teacher_name and inst2:
                            break
                    else:
                        continue
                    break
                t2_title = f"Расписание · {real_name}"
                if inst2:
                    t2_title += f"\n🏛 {inst2}"
                return _fmt_days_paged(days, t2_title,
                                       show_teacher=False, show_group=True)

            return _fmt_search(search_data, intent.query)

        if isinstance(intent, LessonsOnDayIntent):
            data = await _gql(_GQL_LESSONS_DAY, {
                "day": intent.day,
                "gn": intent.group_name, "tn": intent.teacher_name,
                "rn": intent.room_name,  "iname": intent.institute_name,
            })
            nodes = data.get("lessonsOn", {}).get("nodes", [])
            total = data.get("lessonsOn", {}).get("pageInfo", {}).get("totalCount", len(nodes))
            return _fmt_days_paged(
                [{"date": intent.day, "weekdayName": "", "lessons": nodes}],
                f"Занятия {_fmt_date(intent.day)} · {total} пар",
                show_teacher=True, show_group=True,
            )

        if isinstance(intent, OverviewIntent):
            data = await _gql(_GQL_OVERVIEW)
            return _fmt_overview(data.get("overview", {}))

        if isinstance(intent, InstitutesIntent):
            data = await _gql(_GQL_INSTITUTES, {"q": intent.query})
            return _fmt_institutes(data.get("institutes", []))

        if isinstance(intent, UnknownIntent):
            return f"🤔 {intent.clarification_needed}"

        return "❓ Неизвестный запрос."


    text = getattr(message, "_text_override", None) or message.text or message.caption or ""
    tg_id = message.from_user.id if message.from_user else 0

    # Store every incoming message (text, media, forward, reply) immediately
    if tg_id:
        import asyncio as _aio
        _aio.ensure_future(store_message(message))
        # Upsert user profile on every message — most users never run /start,
        # so this is the only reliable place to keep first_name/username fresh.
        if message.from_user:
            _aio.ensure_future(_upsert_user(message.from_user))

    if not text.strip():
        await message.answer("Напишите что-нибудь 🙂")
        return

    placeholder = await message.answer("⏳ Обрабатываю...")

    # Load conversation history for context
    history = await get_history(tg_id)

    try:
        intent_resp = await extract_intent(text, history=history)
        intent = intent_resp.result
    except Exception as exc:
        logger.error(f"intent extraction failed: {exc}")
        await placeholder.edit_text("❌ Не удалось распознать запрос. Попробуйте переформулировать.")
        return

    logger.info(f"intent={intent.intent} user={message.from_user.id if message.from_user else "unknown"}")

    # ── Reply-level cache — skip dispatch entirely if we have a fresh answer ──
    r = get_redis()
    reply_ck = _intent_cache_key(intent)
    reply_ttl = _REPLY_TTL.get(intent.intent, 0)
    if reply_ck and reply_ttl > 0:
        cached_reply = await r.get(reply_ck)
        if cached_reply:
            reply = cached_reply.decode()
            logger.debug(f"reply cache HIT intent={intent.intent}")
            # PAGED strings must never be re-sent from cache as raw text
            _PAGED_PFX = chr(0) + "PAGED" + chr(0)
            if reply.startswith(_PAGED_PFX):
                pass  # fall through to fresh _dispatch below
            else:
                chunks = _split_chunks(reply)
                await placeholder.edit_text(chunks[0], parse_mode="HTML")
                for chunk in chunks[1:]:
                    await message.answer(chunk, parse_mode="HTML")
                return

    # ── Helper: generate short human-readable error ID ────────────────────────
    def _make_error_id() -> str:
        import secrets, string
        chars = string.ascii_uppercase + string.digits
        return "ERR-" + "".join(secrets.choice(chars) for _ in range(6))

    async def _log_bot_error(
        error_id: str,
        exc: Exception,
        intent_name: str = "unknown",
        user_text_: str = "",
    ) -> None:
        """Save bot error to auth_error_logs with error_id for dashboard lookup."""
        import traceback as _tb
        try:
            from app.auth.models import AuthErrorLog
            await AuthErrorLog(
                level="ERROR",
                message=f"[{error_id}] {type(exc).__name__}: {exc}",
                traceback=_tb.format_exc(),
                error_id=error_id,
                tg_id=tg_id or None,
                tg_chat_id=message.chat.id if message.chat else None,
                user_text=user_text_[:500] if user_text_ else None,
                intent=intent_name,
                details={"exc_type": type(exc).__name__},
            ).insert()
        except Exception as _e:
            logger.warning(f"_log_bot_error failed: {_e}")

    _is_error_reply = False   # flag: skip feedback buttons if True

    try:
        reply = await _dispatch(intent)
    except httpx.HTTPError as exc:
        eid = _make_error_id()
        logger.error(f"[{eid}] HTTP error: {exc}")
        _aio.ensure_future(_log_bot_error(eid, exc, getattr(intent, "intent", "unknown"), text))
        reply = f"❌ Ошибка при выполнении запроса.\n<code>{eid}</code>"
        _is_error_reply = True
        try:
            from app.bot.middlewares.anti_flood import quota_error_flag
            quota_error_flag.set(True)
        except Exception:
            pass
    except RuntimeError as exc:
        eid = _make_error_id()
        logger.error(f"[{eid}] GraphQL error: {exc}")
        _aio.ensure_future(_log_bot_error(eid, exc, getattr(intent, "intent", "unknown"), text))
        reply = f"❌ Ошибка при выполнении запроса.\n<code>{eid}</code>"
        _is_error_reply = True
        try:
            from app.bot.middlewares.anti_flood import quota_error_flag
            quota_error_flag.set(True)
        except Exception:
            pass
    except Exception as exc:
        eid = _make_error_id()
        logger.exception(f"[{eid}] dispatch error: {exc}")
        _aio.ensure_future(_log_bot_error(eid, exc, getattr(intent, "intent", "unknown"), text))
        reply = f"❌ Ошибка при выполнении запроса.\n<code>{eid}</code>"
        _is_error_reply = True
        try:
            from app.bot.middlewares.anti_flood import quota_error_flag
            quota_error_flag.set(True)
        except Exception:
            pass

    # ── Disambiguation: multiple groups/rooms found ──────────────────────────
    if reply.startswith(_DISAMBIG_SENTINEL):
        import json as _json
        payload_str = reply[len(_DISAMBIG_SENTINEL):]
        try:
            payload = _json.loads(payload_str)
        except Exception:
            await placeholder.edit_text("❌ Ошибка обработки запроса.")
            return
        candidates  = payload["candidates"]
        intent_type = payload.get("intent_type", "group_schedule")
        dis_key = await _store_disambig(tg_id, payload_str)

        # Filter out candidates with null IDs to prevent broken callback_data
        # (GraphQL can return null groupId/roomId for orphaned records).
        _id_field = "room_id" if intent_type == "room_schedule" else "group_id"
        candidates = [c for c in candidates if c.get(_id_field) is not None]
        if not candidates:
            await placeholder.edit_text(
                f"🔍 По запросу не найдено корректных вариантов. Попробуйте уточнить.",
                parse_mode="HTML",
            )
            return
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        # Build paged disambiguation keyboard
        page_idx   = 0
        total_cands = len(candidates)
        page_cands  = candidates[:_DISAMBIG_PAGE_SIZE]

        buttons = []
        for c in page_cands:
            if intent_type == "room_schedule":
                label   = c["name"]
                bldg    = c.get("building", "")
                if bldg:
                    label += f"  •  {bldg}"
                item_id = c["room_id"]
            else:
                label   = c["name"]
                if c.get("institute_name"):
                    label += f"  •  {c['institute_name']}"
                item_id = c["group_id"]
            buttons.append([InlineKeyboardButton(
                text=label,
                callback_data=f"dis:{dis_key}:{item_id}",
            )])

        # Add pagination row if there are more candidates than fit on one page
        if total_cands > _DISAMBIG_PAGE_SIZE:
            total_pages = (total_cands + _DISAMBIG_PAGE_SIZE - 1) // _DISAMBIG_PAGE_SIZE
            nav_row = [
                InlineKeyboardButton(text=f"1/{total_pages}", callback_data="pg_noop"),
                InlineKeyboardButton(text="След. ▶", callback_data=f"disp:{dis_key}:1"),
            ]
            buttons.append(nav_row)

        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        if intent_type == "room_schedule":
            query_label = intent.room_name if hasattr(intent, "room_name") else "аудитория"
            count_str = f" ({total_cands})" if total_cands > 1 else ""
            prompt = f"🔍 Найдено несколько аудиторий{count_str} по запросу <b>{query_label}</b>.\nВыберите нужную:"
        else:
            query_label = intent.group_name if hasattr(intent, "group_name") else "группа"
            count_str = f" ({total_cands})" if total_cands > 1 else ""
            prompt = f"🔍 Найдено несколько групп{count_str} по запросу <b>{query_label}</b>.\nВыберите нужную:"
        await placeholder.edit_text(prompt, parse_mode="HTML", reply_markup=kb)
        # Save the disambiguation prompt as a bot message so the dashboard shows it
        _aio.ensure_future(store_bot_reply(placeholder, tg_id))
        return

    # Cache the formatted reply — never cache ephemeral markers (PAGED, DISAMBIG)
    _PAGED_PFX = chr(0) + "PAGED" + chr(0)
    if reply_ck and reply_ttl > 0 and not reply.startswith("❌") and not reply.startswith(_PAGED_PFX) and not reply.startswith(_DISAMBIG_SENTINEL):
        try:
            await r.setex(reply_ck, reply_ttl, reply.encode())
        except Exception as exc:
            logger.warning(f"reply cache write failed: {exc}")

    # ── Paged response (multi-day schedule) ───────────────────────────────────
    # IMPORTANT: check the raw reply for the PAGED marker BEFORE _split_chunks,
    # because _split_chunks truncates strings > 4096 chars and would corrupt the JSON.
    if reply.startswith("\x00PAGED\x00"):
        import json as _json
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        _paged_body = reply[7:]  # strip leading \x00PAGED\x00
        # strip trailing \x00 if present
        raw = _paged_body[:-1] if _paged_body.endswith("\x00") else _paged_body
        if not raw or not raw.strip():
            logger.warning(f"Получен пустой ответ для парсинга JSON. User: {message.from_user.id}")
            await placeholder.edit_text("Извините, не удалось получить данные о расписании.")
            return

        try:
            pages: list[str] = _json.loads(raw)
        except _json.JSONDecodeError:
            logger.error(f"Ошибка формата JSON: {raw[:200]}")
            await placeholder.edit_text("Ошибка обработки данных расписания.")
            return
        pk = _page_key(tg_id, raw[:40])
        await _store_pages(pk, pages)
        kb = _make_nav_kb(pk, 0, len(pages))
        # Attach feedback row AFTER we know the actual message_id (placeholder.message_id)
        # placeholder is the "⏳" message that gets edited in-place — its id is stable
        kb = _add_feedback_row(kb, message.chat.id, placeholder.message_id)
        sent = await placeholder.edit_text(
            pages[0] + f"\n\n<i>День 1 из {len(pages)}</i>",
            parse_mode="HTML", reply_markup=kb,
        )
        # Store feedback metadata (question + answer) so dashboard can show it
        if tg_id and sent:
            import asyncio as _aio
            bot_preview = pages[0][:2000]
            _aio.ensure_future(add_message(tg_id, "user", text))
            _aio.ensure_future(add_message(tg_id, "assistant", bot_preview[:400]))
            _aio.ensure_future(_store_feedback_meta(
                sent.chat.id, sent.message_id, text, bot_preview,
            ))
            _aio.ensure_future(store_bot_reply(sent, tg_id))
        return

    chunks = _split_chunks(reply)
    if not chunks:
        await placeholder.edit_text("(пустой ответ)")
        return

    # Send first chunk WITHOUT feedback buttons so we know the real message_id first
    sent = await placeholder.edit_text(chunks[0], parse_mode="HTML")
    for chunk in chunks[1:]:
        await message.answer(chunk, parse_mode="HTML")

    # Attach feedback buttons ONLY for successful (non-error) responses
    if sent and not _is_error_reply:
        fb_kb = _add_feedback_row(None, sent.chat.id, sent.message_id)
        try:
            sent = await sent.edit_reply_markup(reply_markup=fb_kb)
        except Exception:
            pass  # too old or unchanged — skip

    # Persist to conversation memory + full message store (non-blocking)
    if tg_id:
        import asyncio as _aio
        _aio.ensure_future(add_message(tg_id, "user", text))
        _aio.ensure_future(add_message(tg_id, "assistant", reply[:400]))
        if sent and isinstance(sent, Message) and not _is_error_reply:
            # Store feedback metadata: user question + bot answer (skip for error responses)
            _aio.ensure_future(_store_feedback_meta(
                sent.chat.id, sent.message_id, text, reply[:2000]
            ))
            _aio.ensure_future(store_bot_reply(sent, tg_id))
