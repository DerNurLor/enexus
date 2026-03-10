from fastapi import APIRouter, HTTPException, Query
from datetime import date as date_type, datetime
from typing import Optional
from loguru import logger

from app.models.teacher import Teacher

router = APIRouter(prefix="/teachers", tags=["Teachers"])


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
        "first_seen_at":       t.first_seen_at,
        "last_seen_at":        t.last_seen_at,
    }


def _lesson_to_dict(l) -> dict:
    return {
        "subject":      l.subject,
        "lesson_type":  l.lesson_type,
        "time_start":   l.time_start,
        "time_end":     l.time_end,
        "teacher_name": l.teacher_name,
        "teacher_id":   l.teacher_id,
        "room_name":    l.room_name,
        "room_id":      l.room_id,
        "classroom":    l.room_name,
        "group_name":   l.group_name,
        "group_id":     l.group_id,
        "subgroup":     l.subgroup,
        "week_type":    l.week_type,
        "note":         l.note,
        "building":     l.building,
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


@router.get("/{teacher_id}", summary="Get teacher info")
async def get_teacher(teacher_id: int):
    t = await Teacher.find_one(Teacher.teacher_id == teacher_id)
    if not t:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return _teacher_meta(t)


@router.get("/{teacher_id}/day", summary="Teacher schedule for a specific date")
async def get_teacher_day(
    teacher_id: int,
    day: date_type = Query(...),
):
    from app.models.lesson import LessonDoc
    t = await Teacher.find_one(Teacher.teacher_id == teacher_id)
    if not t:
        raise HTTPException(status_code=404, detail="Teacher not found")

    lessons = await LessonDoc.find(
        LessonDoc.teacher_id == teacher_id,
        LessonDoc.date == day,
    ).sort("+time_start").to_list()

    return {
        "teacher_id": teacher_id,
        "name":       t.full_name,
        "date":       day.isoformat(),
        "refreshing": None,
        "lessons":    [_lesson_to_dict(l) for l in lessons],
        "message":    None if lessons else "No classes this day",
    }


@router.get("/{teacher_id}/week", summary="Teacher schedule for an ISO week")
async def get_teacher_week(
    teacher_id: int,
    week: int = Query(..., ge=1, le=53),
):
    from app.models.lesson import LessonDoc
    t = await Teacher.find_one(Teacher.teacher_id == teacher_id)
    if not t:
        raise HTTPException(status_code=404, detail="Teacher not found")

    lessons = await LessonDoc.find(
        LessonDoc.teacher_id == teacher_id,
        LessonDoc.week_number == week,
    ).sort("+date", "+time_start").to_list()

    # Group by date
    days_map: dict = {}
    for l in lessons:
        d = l.date.isoformat()
        if d not in days_map:
            days_map[d] = {"date": d, "week_number": week, "lessons": []}
        days_map[d]["lessons"].append(_lesson_to_dict(l))

    return {
        "teacher_id": teacher_id,
        "name":       t.full_name,
        "week":       week,
        "days":       sorted(days_map.values(), key=lambda d: d["date"]),
    }
