from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from datetime import date as date_type, datetime
from typing import Optional
from loguru import logger

from app.models.teacher import Teacher

router = APIRouter(prefix="/teachers", tags=["Teachers"])

STALE_HOURS      = 24
MIN_FUTURE_WEEKS = 6


def _needs_refresh(scraped_at, schedule: dict) -> tuple[bool, str]:
    """
    Teacher schedules are derived from group data — check staleness only.
    No background HTTP fetch is triggered; refresh happens via the group scrape.
    """
    if not schedule:
        return True, "no schedule yet — will populate after next group scrape"
    if not scraped_at:
        return True, "never scraped"
    age_h = (datetime.utcnow() - scraped_at).total_seconds() / 3600
    if age_h > STALE_HOURS:
        return True, f"stale ({age_h:.1f}h) — refreshes with next group scrape"
    return False, "fresh"


def _teacher_meta(t: Teacher) -> dict:
    return {
        "teacher_id":          t.teacher_id,
        "full_name":           t.full_name,
        "short_name":          t.short_name,
        "institute_ids":       t.institute_ids,
        "institute_names":     t.institute_names,
        "subjects":            t.subjects,
        "lesson_types":        t.lesson_types,
        "group_ids":           t.group_ids,
        "group_names":         t.group_names,
        "schedule_scraped_at": t.schedule_scraped_at,
        "days_count":          len(t.schedule) if t.schedule else 0,
        "first_seen_at":       t.first_seen_at,
        "last_seen_at":        t.last_seen_at,
    }


@router.get("/", summary="List all teachers")
async def list_teachers(
    q:            Optional[str] = Query(None, description="Name substring"),
    subject:      Optional[str] = Query(None),
    lesson_type:  Optional[str] = Query(None),
    institute_id: Optional[int] = Query(None),
    group_id:     Optional[int] = Query(None),
    has_schedule: Optional[bool] = Query(None),
):
    filters: dict = {}
    if q:            filters["full_name"]    = {"$regex": q, "$options": "i"}
    if subject:      filters["subjects"]     = {"$regex": subject, "$options": "i"}
    if lesson_type:  filters["lesson_types"] = {"$regex": lesson_type, "$options": "i"}
    if institute_id: filters["institute_ids"] = institute_id
    if group_id:     filters["group_ids"]    = group_id
    if has_schedule is True:  filters["schedule_scraped_at"] = {"$ne": None}
    if has_schedule is False: filters["schedule_scraped_at"] = None

    teachers = await Teacher.find(filters).sort("full_name").to_list()
    return [_teacher_meta(t) for t in teachers]


@router.get("/{teacher_id}", summary="Get teacher with full schedule")
async def get_teacher(teacher_id: int):
    t = await Teacher.find_one(Teacher.teacher_id == teacher_id)
    if not t:
        raise HTTPException(status_code=404, detail="Teacher not found")

    stale, reason = _needs_refresh(t.schedule_scraped_at, t.schedule or {})
    return {
        **_teacher_meta(t),
        "stale":    reason if stale else None,
        "schedule": t.schedule or {},
    }


@router.get("/{teacher_id}/day", summary="Teacher schedule for a specific date")
async def get_teacher_day(
    teacher_id: int,
    day: date_type = Query(...),
):
    t = await Teacher.find_one(Teacher.teacher_id == teacher_id)
    if not t:
        raise HTTPException(status_code=404, detail="Teacher not found")

    day_str  = day.isoformat()
    day_data = (t.schedule or {}).get(day_str)
    stale, reason = _needs_refresh(t.schedule_scraped_at, t.schedule or {})

    return {
        "teacher_id": teacher_id,
        "full_name":  t.full_name,
        "date":       day_str,
        "stale":      reason if stale else None,
        "lessons":    day_data.get("lessons", []) if day_data else [],
        "message":    None if day_data else "No classes this day",
    }


@router.get("/{teacher_id}/week", summary="Teacher schedule for an ISO week")
async def get_teacher_week(
    teacher_id: int,
    week: int = Query(..., ge=1, le=53),
):
    t = await Teacher.find_one(Teacher.teacher_id == teacher_id)
    if not t:
        raise HTTPException(status_code=404, detail="Teacher not found")

    stale, reason = _needs_refresh(t.schedule_scraped_at, t.schedule or {})
    days = [
        {"date": iso, **day}
        for iso, day in (t.schedule or {}).items()
        if day.get("week_number") == week
    ]

    return {
        "teacher_id": teacher_id,
        "full_name":  t.full_name,
        "week":       week,
        "stale":      reason if stale else None,
        "days":       sorted(days, key=lambda d: d["date"]),
    }
