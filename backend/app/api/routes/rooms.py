from fastapi import APIRouter, HTTPException, Query
from datetime import date as date_type, datetime
from typing import Optional
from loguru import logger

from app.models.room import Room

router = APIRouter(prefix="/rooms", tags=["Rooms"])

STALE_HOURS      = 24
MIN_FUTURE_WEEKS = 6


def _needs_refresh(scraped_at, schedule: dict) -> tuple[bool, str]:
    if not schedule:
        return True, "no schedule yet — will populate after next group scrape"
    if not scraped_at:
        return True, "never scraped"
    age_h = (datetime.utcnow() - scraped_at).total_seconds() / 3600
    if age_h > STALE_HOURS:
        return True, f"stale ({age_h:.1f}h) — refreshes with next group scrape"
    return False, "fresh"


def _room_meta(r: Room) -> dict:
    return {
        "room_id":             r.room_id,
        "name":                r.name,
        "building":            r.building,
        "subjects":            r.subjects,
        "lesson_types":        r.lesson_types,
        "group_ids":           r.group_ids,
        "group_names":         r.group_names,
        "teacher_ids":         r.teacher_ids,
        "teacher_names":       r.teacher_names,
        "schedule_scraped_at": r.schedule_scraped_at,
        "days_count":          len(r.schedule) if r.schedule else 0,
        "last_seen_at":        r.last_seen_at,
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


@router.get("/", summary="List all rooms")
async def list_rooms(
    q:            Optional[str]  = Query(None, description="Room name substring"),
    building:     Optional[str]  = Query(None),
    subject:      Optional[str]  = Query(None),
    teacher_id:   Optional[int]  = Query(None),
    group_id:     Optional[int]  = Query(None),
    has_schedule: Optional[bool] = Query(None),
):
    filters: dict = {}
    if q:          filters["name"]        = {"$regex": q, "$options": "i"}
    if building:   filters["building"]    = {"$regex": building, "$options": "i"}
    if subject:    filters["subjects"]    = {"$regex": subject, "$options": "i"}
    if teacher_id: filters["teacher_ids"] = teacher_id
    if group_id:   filters["group_ids"]   = group_id
    if has_schedule is True:  filters["schedule_scraped_at"] = {"$ne": None}
    if has_schedule is False: filters["schedule_scraped_at"] = None

    rooms = await Room.find(filters).sort("name").to_list()
    return [_room_meta(r) for r in rooms]


@router.get("/buildings-list", summary="List all distinct buildings")
async def list_buildings_simple():
    rooms = await Room.find_all().to_list()
    buildings = sorted({r.building for r in rooms if r.building})
    return {"buildings": buildings}


@router.get("/buildings", summary="All buildings with their rooms")
async def list_buildings():
    rooms = await Room.find_all().sort("name").to_list()
    buildings: dict[str, dict] = {}
    for r in rooms:
        b = r.building or "СКФУ (корпус не определён)"
        if b not in buildings:
            buildings[b] = {"building": b, "rooms_count": 0, "rooms": [], "subjects": set()}
        buildings[b]["rooms"].append(_room_meta(r))
        buildings[b]["rooms_count"] += 1
        buildings[b]["subjects"].update(r.subjects)

    result = []
    for b_data in sorted(buildings.values(), key=lambda x: x["building"]):
        b_data["subjects"] = sorted(b_data["subjects"])
        result.append(b_data)
    return {"total_buildings": len(result), "buildings": result}


@router.get("/free", summary="Free rooms at a given datetime")
async def get_free_rooms(
    at:       str           = Query(..., description="ISO datetime, e.g. 2025-01-15T10:00:00"),
    duration: int           = Query(90,  description="Duration in minutes"),
    building: Optional[str] = Query(None),
):
    """
    Returns all known rooms that have NO lessons overlapping [at, at+duration).
    Uses LessonDoc collection — works even if Room.schedule is not populated.
    """
    from datetime import timedelta, date as date_type
    from app.models.lesson import LessonDoc

    try:
        dt_start = datetime.fromisoformat(at)
    except ValueError:
        raise HTTPException(400, "Invalid datetime. Use ISO 8601: 2025-01-15T10:00:00")

    dt_end  = dt_start + timedelta(minutes=duration)
    day     = dt_start.date()
    t_start = dt_start.strftime("%H:%M")
    t_end   = dt_end.strftime("%H:%M")

    # Find all rooms that HAVE a lesson overlapping the window on this day
    lesson_filters: dict = {
        "date":       day,
        "time_start": {"$lt": t_end},
        "time_end":   {"$gt": t_start},
        "room_id":    {"$ne": None},
    }
    busy_lessons = await LessonDoc.find(lesson_filters).to_list()
    busy_room_ids = {l.room_id for l in busy_lessons}

    # All rooms (optionally filtered by building)
    room_filters: dict = {}
    if building:
        room_filters["building"] = {"$regex": building, "$options": "i"}

    all_rooms = await Room.find(room_filters).sort("name").to_list()

    free = [r for r in all_rooms if r.room_id not in busy_room_ids]

    result_rooms = [
        {
            "roomId":   r.room_id,
            "name":     r.name,
            "building": r.building,
            "capacity": getattr(r, "capacity", None),
        }
        for r in free
    ]

    by_building: dict = {}
    for r in result_rooms:
        key = r.get("building") or "—"
        by_building.setdefault(key, []).append({
            "name":    r["name"],
            "room_id": r["roomId"],
        })

    return {"rooms": result_rooms, "by_building": by_building, "total": len(result_rooms)}


@router.get("/{room_id}", summary="Get room with full schedule")
async def get_room(room_id: int):
    r = await Room.find_one(Room.room_id == room_id)
    if not r:
        raise HTTPException(status_code=404, detail="Room not found")

    stale, reason = _needs_refresh(r.schedule_scraped_at, r.schedule or {})
    return {
        **_room_meta(r),
        "stale":    reason if stale else None,
        "schedule": r.schedule or {},
    }


@router.get("/{room_id}/day", summary="Room schedule for a specific date")
async def get_room_day(
    room_id: int,
    day: date_type = Query(...),
):
    from app.models.lesson import LessonDoc
    r = await Room.find_one(Room.room_id == room_id)
    if not r:
        raise HTTPException(status_code=404, detail="Room not found")

    lessons = await LessonDoc.find(
        LessonDoc.room_id == room_id,
        LessonDoc.date == day,
    ).sort("+time_start").to_list()

    return {
        "room_id":    room_id,
        "name":       r.name,
        "building":   r.building,
        "date":       day.isoformat(),
        "refreshing": None,
        "lessons":    [_lesson_to_dict(l) for l in lessons],
        "message":    None if lessons else "No classes this day",
    }


@router.get("/{room_id}/week", summary="Room schedule for an ISO week")
async def get_room_week(
    room_id: int,
    week: int = Query(..., ge=1, le=53),
):
    from app.models.lesson import LessonDoc
    r = await Room.find_one(Room.room_id == room_id)
    if not r:
        raise HTTPException(status_code=404, detail="Room not found")

    lessons = await LessonDoc.find(
        LessonDoc.room_id == room_id,
        LessonDoc.week_number == week,
    ).sort("+date", "+time_start").to_list()

    days_map: dict = {}
    for l in lessons:
        d = l.date.isoformat()
        if d not in days_map:
            days_map[d] = {"date": d, "week_number": week, "lessons": []}
        days_map[d]["lessons"].append(_lesson_to_dict(l))

    return {
        "room_id":  room_id,
        "name":     r.name,
        "building": r.building,
        "week":     week,
        "days":     sorted(days_map.values(), key=lambda d: d["date"]),
    }
