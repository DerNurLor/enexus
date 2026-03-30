"""
backend/app/api/routes/schedules.py

УЛУЧШЕНИЯ:
  [I1] _refresh_in_progress перенесён из in-process set → Redis.
       При нескольких воркерах uvicorn каждый процесс имел свою копию —
       защита от параллельных refresh не работала. Теперь используем
       Redis SETNX с TTL как distributed lock.
  [I2] Добавлен эндпоинт GET /schedules/group/{id}/export.ics —
       экспорт расписания в формат iCalendar (Google Calendar, Apple Calendar).
       Без внешних зависимостей — только stdlib.
  [I3] /schedules/group/{id}/range ограничен максимум 90 днями.
       Раньше запрос за год выгружал всё расписание без кеширования.
  [I4] Исправлено использование datetime.utcnow() → datetime.now(timezone.utc)
"""
import asyncio
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Response
from datetime import date as date_type, datetime, timedelta, timezone
from loguru import logger

from app.models.group import Group, DaySchedule
from app.scraper.client import NCFUClient, get_monday
from app.scraper.parser import parse_week

router = APIRouter(prefix="/schedules", tags=["Schedules"])

STALE_HOURS      = 24
MIN_FUTURE_WEEKS = 6


# ── [I1] Redis-based distributed refresh lock ─────────────────────────────────

async def _mark_refreshing(group_id: int, ttl: int = 300) -> bool:
    """Возвращает True если удалось захватить lock (никто другой не refreshит)."""
    try:
        from app.cache.redis import get_redis
        r = get_redis()
        # SETNX + EXPIRE атомарно через SET NX EX
        result = await r.set(f"schedule:refresh:{group_id}", "1", ex=ttl, nx=True)
        return result is not None
    except Exception as exc:
        logger.warning(f"Redis refresh lock failed ({group_id}): {exc}")
        return True  # fail open — лучше лишний refresh чем зависание

async def _unmark_refreshing(group_id: int) -> None:
    try:
        from app.cache.redis import get_redis
        await get_redis().delete(f"schedule:refresh:{group_id}")
    except Exception:
        pass

async def _is_refreshing(group_id: int) -> bool:
    try:
        from app.cache.redis import get_redis
        return bool(await get_redis().exists(f"schedule:refresh:{group_id}"))
    except Exception:
        return False


# ── Lesson merge ──────────────────────────────────────────────────────────────

def _merge_lessons(lessons: list) -> list[dict]:
    merged: dict[tuple, dict] = {}

    for l in lessons:
        key = (
            str(l.date) if hasattr(l, "date") else l.get("date", ""),
            l.time_start  if hasattr(l, "time_start")  else l.get("time_start", ""),
            l.time_end    if hasattr(l, "time_end")     else l.get("time_end", ""),
            l.subject     if hasattr(l, "subject")      else l.get("subject", ""),
            l.teacher_id  if hasattr(l, "teacher_id")   else l.get("teacher_id"),
            l.room_id     if hasattr(l, "room_id")      else l.get("room_id"),
            l.lesson_type if hasattr(l, "lesson_type")  else l.get("lesson_type"),
            l.subgroup    if hasattr(l, "subgroup")     else l.get("subgroup"),
            l.week_type   if hasattr(l, "week_type")    else l.get("week_type"),
        )

        gid   = l.group_id   if hasattr(l, "group_id")   else l.get("group_id")
        gname = l.group_name if hasattr(l, "group_name") else l.get("group_name", "")

        if key not in merged:
            merged[key] = {
                "subject":      l.subject      if hasattr(l, "subject")      else l.get("subject", ""),
                "lesson_type":  l.lesson_type  if hasattr(l, "lesson_type")  else l.get("lesson_type"),
                "time_start":   l.time_start   if hasattr(l, "time_start")   else l.get("time_start", ""),
                "time_end":     l.time_end     if hasattr(l, "time_end")     else l.get("time_end", ""),
                "teacher_name": l.teacher_name if hasattr(l, "teacher_name") else l.get("teacher_name"),
                "teacher_id":   l.teacher_id   if hasattr(l, "teacher_id")   else l.get("teacher_id"),
                "classroom":    l.room_name    if hasattr(l, "room_name")    else l.get("room_name"),
                "room_name":    l.room_name    if hasattr(l, "room_name")    else l.get("room_name"),
                "room_id":      l.room_id      if hasattr(l, "room_id")      else l.get("room_id"),
                "subgroup":     l.subgroup     if hasattr(l, "subgroup")     else l.get("subgroup"),
                "week_type":    l.week_type    if hasattr(l, "week_type")    else l.get("week_type"),
                "note":         l.note         if hasattr(l, "note")         else l.get("note"),
                "_groups": [{"id": gid, "name": gname}] if gid else [],
            }
        else:
            existing_ids = {g["id"] for g in merged[key]["_groups"]}
            if gid and gid not in existing_ids:
                merged[key]["_groups"].append({"id": gid, "name": gname})

    result = []
    for item in merged.values():
        groups = sorted(item.pop("_groups"), key=lambda g: g["name"])
        item["groups"] = groups
        if len(groups) == 1:
            item["group_id"]    = groups[0]["id"]
            item["group_name"]  = groups[0]["name"]
            item["group_names"] = [groups[0]["name"]]
        else:
            item["group_id"]    = None
            item["group_name"]  = ", ".join(g["name"] for g in groups)
            item["group_names"] = [g["name"] for g in groups]
        result.append(item)

    return result


# ── Staleness check ───────────────────────────────────────────────────────────

def _needs_refresh(group: Group) -> tuple[bool, str]:
    if not group.schedule:
        return True, "no schedule"
    if not group.schedule_scraped_at:
        return True, "never scraped"
    # [I4]
    age_h = (datetime.now(timezone.utc) - group.schedule_scraped_at.replace(tzinfo=timezone.utc)
             if group.schedule_scraped_at.tzinfo is None
             else datetime.now(timezone.utc) - group.schedule_scraped_at
             ).total_seconds() / 3600
    if age_h > STALE_HOURS:
        return True, f"stale ({age_h:.1f}h)"
    today = date_type.today()
    future_weeks: set[tuple] = set()
    for iso in group.schedule:
        try:
            d = date_type.fromisoformat(iso)
            if d >= today:
                future_weeks.add(d.isocalendar()[:2])
        except ValueError:
            pass
    if len(future_weeks) < MIN_FUTURE_WEEKS:
        return True, f"only {len(future_weeks)} future weeks"
    return False, "fresh"


# ── Background refresh ────────────────────────────────────────────────────────

async def _do_refresh(group_id: int, group_name: str) -> None:
    # [I1] Distributed lock через Redis
    if not await _mark_refreshing(group_id):
        logger.debug(f"Refresh already running for {group_name} ({group_id}) — skipped")
        return

    logger.info(f"⟳ Background refresh started: {group_name} ({group_id})")

    try:
        async with NCFUClient() as client:
            anchor = await client.get_anchor_monday(group_id)
            if anchor is None:
                anchor = get_monday(date_type.today())

            EMPTY_LIMIT = 4
            full: dict[str, DaySchedule] = {}

            streak, monday = 0, anchor - timedelta(weeks=1)
            while streak < EMPTY_LIMIT:
                raw = await client.get_week_schedule(group_id, monday)
                week = parse_week(raw, monday)
                if week:
                    full.update(week)
                    streak = 0
                else:
                    streak += 1
                monday -= timedelta(weeks=1)

            raw = await client.get_week_schedule(group_id, anchor)
            full.update(parse_week(raw, anchor))

            streak, monday = 0, anchor + timedelta(weeks=1)
            while streak < EMPTY_LIMIT:
                raw = await client.get_week_schedule(group_id, monday)
                week = parse_week(raw, monday)
                if week:
                    full.update(week)
                    streak = 0
                else:
                    streak += 1
                monday += timedelta(weeks=1)

        if full:
            await Group.find_one(Group.group_id == group_id).update({"$set": {
                "schedule":            {k: v.model_dump() for k, v in full.items()},
                "schedule_scraped_at": datetime.now(timezone.utc),  # [I4]
            }})
            logger.info(f"⟳ Background refresh done: {group_name} ({group_id}) — {len(full)} days saved")
        else:
            logger.info(f"⟳ Background refresh: {group_name} ({group_id}) — no data found")

    except Exception as exc:
        logger.warning(f"⟳ Background refresh failed: {group_name} ({group_id}): {type(exc).__name__}: {exc}")
    finally:
        await _unmark_refreshing(group_id)  # [I1]


async def _maybe_refresh(background_tasks: BackgroundTasks, group: Group) -> str | None:
    needs, reason = _needs_refresh(group)
    if needs and not await _is_refreshing(group.group_id):
        background_tasks.add_task(_do_refresh, group.group_id, group.name)
        return reason
    return None


# ── Serializers ───────────────────────────────────────────────────────────────

def _schedule_dict(group: Group) -> dict:
    return {k: v.model_dump() for k, v in group.schedule.items()} if group.schedule else {}


def _lesson_to_dict(l) -> dict:
    return {
        "subject":      l.subject,
        "lesson_type":  l.lesson_type,
        "time_start":   l.time_start,
        "time_end":     l.time_end,
        "teacher_name": l.teacher_name,
        "teacher_id":   l.teacher_id,
        "classroom":    l.room_name,
        "room_name":    l.room_name,
        "room_id":      l.room_id,
        "group_name":   l.group_name,
        "group_names":  [l.group_name] if l.group_name else [],
        "groups":       [{"id": l.group_id, "name": l.group_name}] if l.group_id else [],
        "group_id":     l.group_id,
        "subgroup":     l.subgroup,
        "week_type":    l.week_type,
        "note":         l.note,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/group/{group_id}", summary="Full schedule for a group")
async def get_group_schedule(group_id: int, background_tasks: BackgroundTasks):
    group = await Group.find_one(Group.group_id == group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    refresh_reason = await _maybe_refresh(background_tasks, group)
    return {
        "group_id":            group.group_id,
        "name":                group.name,
        "academic_year":       group.academic_year,
        "schedule_scraped_at": group.schedule_scraped_at,
        "days_count":          len(group.schedule) if group.schedule else 0,
        "refreshing":          refresh_reason,
        "schedule":            _schedule_dict(group),
    }


@router.get("/group/{group_id}/day", summary="Schedule for a specific date (YYYY-MM-DD)")
async def get_schedule_for_day(
    group_id: int,
    background_tasks: BackgroundTasks,
    day: date_type = Query(...),
):
    from app.models.lesson import LessonDoc
    group = await Group.find_one(Group.group_id == group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    lessons = await LessonDoc.find(
        LessonDoc.group_id == group_id,
        LessonDoc.date == day,
    ).sort("+time_start").to_list()

    return {
        "group_id":   group_id,
        "name":       group.name,
        "date":       day.isoformat(),
        "refreshing": None,
        "lessons":    [_lesson_to_dict(l) for l in lessons],
        "message":    None if lessons else "No classes this day",
    }


@router.get("/group/{group_id}/week", summary="Schedule for a specific ISO week number")
async def get_schedule_for_week(
    group_id: int,
    background_tasks: BackgroundTasks,
    week: int = Query(..., ge=1, le=53),
):
    group = await Group.find_one(Group.group_id == group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    refresh_reason = await _maybe_refresh(background_tasks, group)
    days = []
    if group.schedule:
        days = [
            {"date": iso, **day.model_dump()}
            for iso, day in group.schedule.items()
            if day.week_number == week
        ]
    return {
        "group_id":   group_id,
        "name":       group.name,
        "week":       week,
        "refreshing": refresh_reason,
        "days":       sorted(days, key=lambda d: d["date"]),
    }


@router.get("/group/{group_id}/range", summary="Schedule between two dates")
async def get_schedule_for_range(
    group_id: int,
    background_tasks: BackgroundTasks,
    from_date: date_type = Query(...),
    to_date:   date_type = Query(...),
):
    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date must be before to_date")
    # [I3] Ограничение диапазона — без этого запрос за год выгружал всё без кеша
    if (to_date - from_date).days > 90:
        raise HTTPException(status_code=400, detail="Максимальный диапазон — 90 дней")

    group = await Group.find_one(Group.group_id == group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    refresh_reason = await _maybe_refresh(background_tasks, group)
    days = []
    if group.schedule:
        days = [
            {"date": iso, **day.model_dump()}
            for iso, day in group.schedule.items()
            if from_date.isoformat() <= iso <= to_date.isoformat()
        ]
    return {
        "group_id":   group_id,
        "name":       group.name,
        "from_date":  from_date.isoformat(),
        "to_date":    to_date.isoformat(),
        "refreshing": refresh_reason,
        "days":       sorted(days, key=lambda d: d["date"]),
    }


@router.get("/group/{group_id}/export.ics", summary="Export schedule as iCalendar (.ics)")
async def export_ics(
    group_id: int,
    weeks: int = Query(4, ge=1, le=16, description="Число недель от сегодня"),
):
    """
    [I2] Экспорт расписания в формат iCalendar.
    Открывается в Google Calendar, Apple Calendar, Outlook.
    Пример: /schedules/group/123/export.ics?weeks=8
    """
    from app.models.lesson import LessonDoc

    group = await Group.find_one(Group.group_id == group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    today     = date_type.today()
    date_to   = today + timedelta(weeks=weeks)

    lessons = await LessonDoc.find(
        LessonDoc.group_id == group_id,
        LessonDoc.date >= today,
        LessonDoc.date <= date_to,
    ).sort("+date").to_list()

    def _dt(d: date_type, t: str) -> str:
        """Форматируем дату+время в iCal формат: 20240912T083000"""
        hh, mm = t.split(":") if t and ":" in t else ("00", "00")
        return f"{d.strftime('%Y%m%d')}T{hh}{mm}00"

    def _escape(s: str) -> str:
        return (s or "").replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//NCFU Schedule Bot//RU",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Расписание {group.name}",
        "X-WR-TIMEZONE:Europe/Moscow",
        "X-WR-CALDESC:Расписание занятий СКФУ",
    ]

    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for lesson in lessons:
        uid = f"{lesson.id}@ncfu.schedule"
        dtstart = _dt(lesson.date, lesson.time_start)
        dtend   = _dt(lesson.date, lesson.time_end)

        summary = _escape(lesson.subject or "Занятие")
        if lesson.lesson_type:
            summary += f" ({_escape(lesson.lesson_type)})"
        if lesson.subgroup:
            summary += f" — {_escape(lesson.subgroup)}"

        location = _escape(lesson.room_name or "")
        teacher  = _escape(lesson.teacher_name or "")

        description_parts = []
        if teacher:
            description_parts.append(f"Преподаватель: {teacher}")
        if lesson.note:
            description_parts.append(_escape(lesson.note))
        description = "\\n".join(description_parts)

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;TZID=Europe/Moscow:{dtstart}",
            f"DTEND;TZID=Europe/Moscow:{dtend}",
            f"SUMMARY:{summary}",
        ]
        if location:
            lines.append(f"LOCATION:{location}")
        if description:
            lines.append(f"DESCRIPTION:{description}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    content = "\r\n".join(lines) + "\r\n"

    # RFC 5987: filename* с UTF-8 кодированием для поддержки кириллицы.
    # Starlette кодирует заголовки в latin-1, поэтому обычный filename="..." с кириллицей
    # вызывает UnicodeEncodeError. Используем filename*=UTF-8''<percent-encoded> (RFC 5987).
    from urllib.parse import quote as _quote
    safe_name = group.name.replace(" ", "_")
    ascii_name = safe_name.encode("ascii", errors="ignore").decode() or "schedule"
    ascii_filename = f"{ascii_name}_schedule.ics"
    utf8_filename  = f"{safe_name}_schedule.ics"
    encoded        = _quote(utf8_filename, safe="")
    content_disposition = (
        f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded}'
    )

    return Response(
        content=content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": content_disposition,
            "Cache-Control": "no-cache",
        },
    )


@router.get("/teacher/{teacher_id}/day", summary="Schedule for a teacher on a specific date")
async def get_teacher_day(
    teacher_id: int,
    day: date_type = Query(...),
):
    from app.models.lesson import LessonDoc
    from app.models.teacher import Teacher
    teacher = await Teacher.find_one(Teacher.teacher_id == teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    lessons = await LessonDoc.find(
        LessonDoc.teacher_id == teacher_id,
        LessonDoc.date == day,
    ).sort("+time_start").to_list()

    merged = _merge_lessons(lessons)
    merged.sort(key=lambda x: x["time_start"])

    return {
        "teacher_id": teacher_id,
        "name":       teacher.full_name,
        "date":       day.isoformat(),
        "refreshing": None,
        "lessons":    merged,
        "message":    None if merged else "No classes this day",
    }


@router.get("/room/{room_id}/day", summary="Schedule for a room on a specific date")
async def get_room_day(
    room_id: int,
    day: date_type = Query(...),
):
    from app.models.lesson import LessonDoc
    from app.models.room import Room
    room = await Room.find_one(Room.room_id == room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    lessons = await LessonDoc.find(
        LessonDoc.room_id == room_id,
        LessonDoc.date == day,
    ).sort("+time_start").to_list()

    merged = _merge_lessons(lessons)
    merged.sort(key=lambda x: x["time_start"])

    return {
        "room_id":    room_id,
        "name":       room.name,
        "date":       day.isoformat(),
        "refreshing": None,
        "lessons":    merged,
        "message":    None if merged else "No classes this day",
    }
