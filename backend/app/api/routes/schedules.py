import asyncio
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from datetime import date as date_type, datetime, timedelta
from loguru import logger

from app.models.group import Group, DaySchedule
from app.scraper.client import NCFUClient, get_monday
from app.scraper.parser import parse_week

router = APIRouter(prefix="/schedules", tags=["Schedules"])

STALE_HOURS = 24
MIN_FUTURE_WEEKS = 6

_refresh_in_progress: set[int] = set()


# ── Lesson merge ──────────────────────────────────────────────────────────────

def _merge_lessons(lessons: list) -> list[dict]:
    """
    Merge duplicate lessons that happen simultaneously across multiple groups.
    Key: date, time_start, time_end, subject, teacher_id, room_id, lesson_type, subgroup, week_type
    Result includes groups: [{id, name}] for each merged group.
    """
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
    age_h = (datetime.utcnow() - group.schedule_scraped_at).total_seconds() / 3600
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
    if group_id in _refresh_in_progress:
        logger.debug(f"Refresh already running for {group_name} ({group_id}) — skipped")
        return

    _refresh_in_progress.add(group_id)
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
                "schedule_scraped_at": datetime.utcnow(),
            }})
            logger.info(f"⟳ Background refresh done: {group_name} ({group_id}) — {len(full)} days saved")
        else:
            logger.info(f"⟳ Background refresh: {group_name} ({group_id}) — no data found")

    except Exception as exc:
        logger.warning(f"⟳ Background refresh failed: {group_name} ({group_id}): {type(exc).__name__}: {exc}")
    finally:
        _refresh_in_progress.discard(group_id)


def _maybe_refresh(background_tasks: BackgroundTasks, group: Group) -> str | None:
    needs, reason = _needs_refresh(group)
    if needs and group.group_id not in _refresh_in_progress:
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
    refresh_reason = _maybe_refresh(background_tasks, group)
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
    refresh_reason = _maybe_refresh(background_tasks, group)
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
    group = await Group.find_one(Group.group_id == group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    refresh_reason = _maybe_refresh(background_tasks, group)
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
