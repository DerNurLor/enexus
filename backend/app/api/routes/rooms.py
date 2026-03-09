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
    if q:          filters["name"]       = {"$regex": q, "$options": "i"}
    if building:   filters["building"]   = {"$regex": building, "$options": "i"}
    if subject:    filters["subjects"]   = {"$regex": subject, "$options": "i"}
    if teacher_id: filters["teacher_ids"] = teacher_id
    if group_id:   filters["group_ids"]  = group_id
    if has_schedule is True:  filters["schedule_scraped_at"] = {"$ne": None}
    if has_schedule is False: filters["schedule_scraped_at"] = None

    rooms = await Room.find(filters).sort("name").to_list()
    return [_room_meta(r) for r in rooms]


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
    r = await Room.find_one(Room.room_id == room_id)
    if not r:
        raise HTTPException(status_code=404, detail="Room not found")

    day_str  = day.isoformat()
    day_data = (r.schedule or {}).get(day_str)
    stale, reason = _needs_refresh(r.schedule_scraped_at, r.schedule or {})

    return {
        "room_id":  room_id,
        "name":     r.name,
        "building": r.building,
        "date":     day_str,
        "stale":    reason if stale else None,
        "lessons":  day_data.get("lessons", []) if day_data else [],
        "message":  None if day_data else "No classes this day",
    }


@router.get("/{room_id}/week", summary="Room schedule for an ISO week")
async def get_room_week(
    room_id: int,
    week: int = Query(..., ge=1, le=53),
):
    r = await Room.find_one(Room.room_id == room_id)
    if not r:
        raise HTTPException(status_code=404, detail="Room not found")

    stale, reason = _needs_refresh(r.schedule_scraped_at, r.schedule or {})
    days = [
        {"date": iso, **day}
        for iso, day in (r.schedule or {}).items()
        if day.get("week_number") == week
    ]

    return {
        "room_id":  room_id,
        "name":     r.name,
        "building": r.building,
        "week":     week,
        "stale":    reason if stale else None,
        "days":     sorted(days, key=lambda d: d["date"]),
    }
