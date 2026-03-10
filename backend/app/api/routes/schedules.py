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

# Group IDs currently being refreshed — prevents duplicate background fetches
_refresh_in_progress: set[int] = set()


# ── Staleness check ───────────────────────────────────────────────────────────

def _needs_refresh(group: Group) -> tuple[bool, str]:
    """Non-blocking check. Returns (needs_refresh, reason)."""
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
    """
    Fetch the full schedule for a group and save it to MongoDB.
    Runs in the background — never blocks the HTTP response.
    """
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

            # Walk backward
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

            # Anchor week
            raw = await client.get_week_schedule(group_id, anchor)
            full.update(parse_week(raw, anchor))

            # Walk forward
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
    """
    Schedule a background refresh if the group's schedule needs updating.
    Returns the reason string if refresh was scheduled, None if fresh.
    """
    needs, reason = _needs_refresh(group)
    if needs and group.group_id not in _refresh_in_progress:
        background_tasks.add_task(_do_refresh, group.group_id, group.name)
        return reason
    return None


# ── Serializers ───────────────────────────────────────────────────────────────

def _schedule_dict(group: Group) -> dict:
    return {k: v.model_dump() for k, v in group.schedule.items()} if group.schedule else {}


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
        "refreshing":          refresh_reason,   # None = data is fresh, str = reason for background update
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

    day_str = day.isoformat()

    return {
        "group_id":   group_id,
        "name":       group.name,
        "date":       day_str,
        "refreshing": None,
        "lessons":    [
            {
                "subject":      l.subject,
                "lesson_type":  l.lesson_type,
                "time_start":   l.time_start,
                "time_end":     l.time_end,
                "teacher_name": l.teacher_name,
                "teacher_id":   l.teacher_id,
                "classroom":    l.room_name,
                "room_name":    l.room_name,
                "subgroup":     l.subgroup,
                "week_type":    l.week_type,
                "note":         l.note,
            }
            for l in lessons
        ],
        "message": None if lessons else "No classes this day",
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
