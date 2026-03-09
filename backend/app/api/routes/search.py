"""
/api/v1/search — Flexible search across all entities and schedules.

Endpoints:
  GET /search/                       — universal search across groups/teachers/rooms
  GET /search/teachers               — rich teacher search
  GET /search/rooms                  — rich room search
  GET /search/groups                 — rich group search
  GET /search/lessons                — search lessons by subject/type/teacher/room across all entities
  GET /search/now                    — what's happening right now (all entity types)
  GET /search/at                     — what's happening at a specific datetime
  GET /search/day                    — full schedule for all entities on a date
  GET /search/week                   — full schedule for all entities in a week
  GET /search/range                  — schedule in a date range
  GET /search/next                   — next upcoming lesson(s) for a teacher/room/group
  GET /search/free-rooms             — rooms with no lessons at a given time
  GET /search/teacher-groups         — which groups does a teacher teach (with schedule)
  GET /search/conflicts              — find scheduling conflicts (same teacher/room at same time)
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import date as date_type, datetime, time as time_type, timedelta
from typing import Optional
from loguru import logger

from app.models.group import Group, Lesson
from app.models.teacher import Teacher
from app.models.room import Room

router = APIRouter(prefix="/search", tags=["Search"])


# ── Shared helpers ────────────────────────────────────────────────────────────

def _parse_time(s: str) -> time_type:
    """Parse HH:MM string into time object."""
    h, m = s.split(":")
    return time_type(int(h), int(m))


def _lesson_active_at(lesson: dict, check_time: time_type) -> bool:
    try:
        return _parse_time(lesson["time_start"]) <= check_time <= _parse_time(lesson["time_end"])
    except Exception:
        return False


def _lesson_starts_after(lesson: dict, after_time: time_type) -> bool:
    try:
        return _parse_time(lesson["time_start"]) >= after_time
    except Exception:
        return False


def _day_data_to_dict(day_data) -> dict:
    """DaySchedule model or plain dict → plain dict with lessons as list of dicts."""
    if hasattr(day_data, "model_dump"):
        return day_data.model_dump()
    return day_data


def _lesson_to_dict(lesson) -> dict:
    if hasattr(lesson, "model_dump"):
        return lesson.model_dump()
    return lesson


def _iter_schedule(schedule: dict):
    """Yield (iso_date_str, day_dict) from any schedule dict."""
    for iso, day in schedule.items():
        yield iso, _day_data_to_dict(day)


def _matches_lesson_filters(
    lesson: dict,
    subject: Optional[str],
    lesson_type: Optional[str],
    teacher_name: Optional[str],
    room_name: Optional[str],
) -> bool:
    if subject and subject.lower() not in (lesson.get("subject") or "").lower():
        return False
    if lesson_type and lesson_type.lower() not in (lesson.get("lesson_type") or "").lower():
        return False
    if teacher_name and teacher_name.lower() not in (lesson.get("teacher_name") or "").lower():
        return False
    if room_name and room_name.lower() not in (lesson.get("classroom") or "").lower():
        return False
    return True


# ── 1. Universal search ───────────────────────────────────────────────────────

@router.get("/", summary="Universal search across groups, teachers, and rooms")
async def universal_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Search all entity types simultaneously.
    Returns matched groups, teachers, and rooms in one response.
    """
    regex = {"$regex": q, "$options": "i"}

    groups = await Group.find({"name": regex}).limit(limit).to_list()
    teachers = await Teacher.find({"$or": [
        {"full_name": regex},
        {"subjects": regex},
    ]}).limit(limit).to_list()
    rooms = await Room.find({"$or": [
        {"name": regex},
        {"building": regex},
    ]}).limit(limit).to_list()

    return {
        "query": q,
        "results": {
            "groups": [
                {"group_id": g.group_id, "name": g.name, "institute_name": g.institute_name,
                 "speciality_name": g.speciality_name, "course": g.course}
                for g in groups
            ],
            "teachers": [
                {"teacher_id": t.teacher_id, "full_name": t.full_name,
                 "subjects": t.subjects[:5], "institute_names": t.institute_names}
                for t in teachers
            ],
            "rooms": [
                {"room_id": r.room_id, "name": r.name, "building": r.building,
                 "subjects": r.subjects[:5]}
                for r in rooms
            ],
        },
        "counts": {
            "groups": len(groups),
            "teachers": len(teachers),
            "rooms": len(rooms),
        }
    }


# ── 2. Teacher search ─────────────────────────────────────────────────────────

@router.get("/teachers", summary="Search teachers with rich filters")
async def search_teachers(
    q:            Optional[str] = Query(None, description="Name substring"),
    subject:      Optional[str] = Query(None, description="Subject they teach"),
    lesson_type:  Optional[str] = Query(None, description="Lesson type (Лекция, Практика...)"),
    institute_id: Optional[int] = Query(None),
    group_id:     Optional[int] = Query(None, description="Teachers who teach this group"),
    has_schedule: Optional[bool] = Query(None, description="Only teachers with scraped schedule"),
    limit:        int            = Query(50, ge=1, le=500),
):
    filters: dict = {}
    if q:            filters["full_name"]    = {"$regex": q, "$options": "i"}
    if subject:      filters["subjects"]     = {"$regex": subject, "$options": "i"}
    if lesson_type:  filters["lesson_types"] = {"$regex": lesson_type, "$options": "i"}
    if institute_id: filters["institute_ids"] = institute_id
    if group_id:     filters["group_ids"]    = group_id
    if has_schedule is True:
        filters["schedule_scraped_at"] = {"$ne": None}
    elif has_schedule is False:
        filters["schedule_scraped_at"] = None

    teachers = await Teacher.find(filters).sort("full_name").limit(limit).to_list()

    return {
        "total": len(teachers),
        "teachers": [
            {
                "teacher_id":      t.teacher_id,
                "full_name":       t.full_name,
                "short_name":      t.short_name,
                "institute_names": t.institute_names,
                "subjects":        t.subjects,
                "lesson_types":    t.lesson_types,
                "group_count":     len(t.group_ids),
                "has_schedule":    bool(t.schedule),
                "schedule_scraped_at": t.schedule_scraped_at,
            }
            for t in teachers
        ]
    }


# ── 3. Room search ────────────────────────────────────────────────────────────

@router.get("/rooms", summary="Search rooms with rich filters")
async def search_rooms(
    q:            Optional[str] = Query(None, description="Room name substring"),
    building:     Optional[str] = Query(None),
    subject:      Optional[str] = Query(None, description="Subject taught here"),
    teacher_id:   Optional[int] = Query(None, description="Rooms used by this teacher"),
    group_id:     Optional[int] = Query(None, description="Rooms used by this group"),
    has_schedule: Optional[bool] = Query(None),
    limit:        int            = Query(50, ge=1, le=500),
):
    filters: dict = {}
    if q:          filters["name"]       = {"$regex": q, "$options": "i"}
    if building:   filters["building"]   = {"$regex": building, "$options": "i"}
    if subject:    filters["subjects"]   = {"$regex": subject, "$options": "i"}
    if teacher_id: filters["teacher_ids"] = teacher_id
    if group_id:   filters["group_ids"]  = group_id
    if has_schedule is True:
        filters["schedule_scraped_at"] = {"$ne": None}
    elif has_schedule is False:
        filters["schedule_scraped_at"] = None

    rooms = await Room.find(filters).sort("name").limit(limit).to_list()

    return {
        "total": len(rooms),
        "rooms": [
            {
                "room_id":      r.room_id,
                "name":         r.name,
                "building":     r.building,
                "subjects":     r.subjects,
                "group_count":  len(r.group_ids),
                "teacher_count": len(r.teacher_ids),
                "has_schedule": bool(r.schedule),
                "schedule_scraped_at": r.schedule_scraped_at,
            }
            for r in rooms
        ]
    }


# ── 4. Group search ───────────────────────────────────────────────────────────

@router.get("/groups", summary="Search groups with rich filters")
async def search_groups(
    q:            Optional[str] = Query(None, description="Group name substring"),
    institute_id: Optional[int] = Query(None),
    speciality:   Optional[str] = Query(None, description="Speciality name substring"),
    course:       Optional[int] = Query(None, ge=1, le=6),
    has_schedule: Optional[bool] = Query(None),
    limit:        int            = Query(50, ge=1, le=500),
):
    filters: dict = {}
    if q:            filters["name"]           = {"$regex": q, "$options": "i"}
    if institute_id: filters["institute_id"]   = institute_id
    if speciality:   filters["speciality_name"] = {"$regex": speciality, "$options": "i"}
    if course:       filters["course"]         = course
    if has_schedule is True:
        filters["schedule_scraped_at"] = {"$ne": None}
    elif has_schedule is False:
        filters["schedule_scraped_at"] = None

    groups = await Group.find(filters).sort("name").limit(limit).to_list()

    return {
        "total": len(groups),
        "groups": [
            {
                "group_id":        g.group_id,
                "name":            g.name,
                "institute_name":  g.institute_name,
                "speciality_name": g.speciality_name,
                "course":          g.course,
                "academic_year":   g.academic_year,
                "has_schedule":    bool(g.schedule),
                "days_count":      len(g.schedule),
                "schedule_scraped_at": g.schedule_scraped_at,
            }
            for g in groups
        ]
    }


# ── 5. Lesson search (across all schedules) ───────────────────────────────────

@router.get("/lessons", summary="Search lessons by subject, type, teacher, or room across all entities")
async def search_lessons(
    subject:      Optional[str]       = Query(None, description="Subject name substring"),
    lesson_type:  Optional[str]       = Query(None, description="e.g. Лекция"),
    teacher_name: Optional[str]       = Query(None),
    room_name:    Optional[str]       = Query(None),
    from_date:    Optional[date_type] = Query(None),
    to_date:      Optional[date_type] = Query(None),
    entity_type:  Optional[str]       = Query(None, description="group | teacher | room — omit for all"),
    limit:        int                 = Query(100, ge=1, le=1000),
):
    """
    Walk all schedules in DB and return matching lessons with their context
    (which group/teacher/room, which date and time).
    """
    from_iso = from_date.isoformat() if from_date else None
    to_iso   = to_date.isoformat()   if to_date   else None

    results = []

    async def scan_schedule(schedule: dict, entity_type_str: str, entity_id: int, entity_name: str):
        for iso, day in _iter_schedule(schedule):
            if from_iso and iso < from_iso:
                continue
            if to_iso and iso > to_iso:
                continue
            for lesson in day.get("lessons", []):
                if not _matches_lesson_filters(lesson, subject, lesson_type, teacher_name, room_name):
                    continue
                results.append({
                    "entity_type": entity_type_str,
                    "entity_id":   entity_id,
                    "entity_name": entity_name,
                    "date":        iso,
                    "weekday_name": day.get("weekday_name"),
                    "week_number": day.get("week_number"),
                    **lesson,
                })
                if len(results) >= limit:
                    return

    if entity_type in (None, "group"):
        groups = await Group.find({"schedule": {"$ne": {}}}).to_list()
        for g in groups:
            if len(results) >= limit:
                break
            await scan_schedule(g.schedule, "group", g.group_id, g.name)

    if entity_type in (None, "teacher") and len(results) < limit:
        teachers = await Teacher.find({"schedule": {"$ne": {}}}).to_list()
        for t in teachers:
            if len(results) >= limit:
                break
            await scan_schedule(t.schedule, "teacher", t.teacher_id, t.full_name)

    if entity_type in (None, "room") and len(results) < limit:
        rooms = await Room.find({"schedule": {"$ne": {}}}).to_list()
        for r in rooms:
            if len(results) >= limit:
                break
            await scan_schedule(r.schedule, "room", r.room_id, r.name)

    results.sort(key=lambda x: (x["date"], x.get("time_start", "")))
    return {"total": len(results), "lessons": results}


# ── 6. What's happening RIGHT NOW ─────────────────────────────────────────────

@router.get("/now", summary="All lessons currently in progress")
async def lessons_now(
    entity_type:  Optional[str] = Query(None, description="group | teacher | room"),
    institute_id: Optional[int] = Query(None),
):
    now = datetime.now()
    today_iso = now.date().isoformat()
    now_time  = now.time().replace(second=0, microsecond=0)

    return await _lessons_at_time(today_iso, now_time, entity_type, institute_id)


# ── 7. What's happening AT a specific datetime ────────────────────────────────

@router.get("/at", summary="All lessons at a specific date and time")
async def lessons_at(
    dt:           datetime            = Query(..., description="ISO datetime e.g. 2026-03-10T10:00"),
    entity_type:  Optional[str]       = Query(None, description="group | teacher | room"),
    institute_id: Optional[int]       = Query(None),
):
    date_iso = dt.date().isoformat()
    check_time = dt.time().replace(second=0, microsecond=0)

    return await _lessons_at_time(date_iso, check_time, entity_type, institute_id)


async def _lessons_at_time(date_iso: str, check_time: time_type, entity_type, institute_id):
    results = []

    async def scan(schedule: dict, etype: str, eid: int, ename: str):
        day = schedule.get(date_iso)
        if not day:
            return
        day_dict = _day_data_to_dict(day)
        for lesson in day_dict.get("lessons", []):
            if _lesson_active_at(lesson, check_time):
                results.append({
                    "entity_type": etype,
                    "entity_id":   eid,
                    "entity_name": ename,
                    "date":        date_iso,
                    **lesson,
                })

    if entity_type in (None, "group"):
        q = {"schedule": {"$ne": {}}}
        if institute_id:
            q["institute_id"] = institute_id
        for g in await Group.find(q).to_list():
            await scan(g.schedule, "group", g.group_id, g.name)

    if entity_type in (None, "teacher"):
        for t in await Teacher.find({"schedule": {"$ne": {}}}).to_list():
            await scan(t.schedule, "teacher", t.teacher_id, t.full_name)

    if entity_type in (None, "room"):
        for r in await Room.find({"schedule": {"$ne": {}}}).to_list():
            await scan(r.schedule, "room", r.room_id, r.name)

    results.sort(key=lambda x: x.get("time_start", ""))
    return {
        "date":       date_iso,
        "time":       check_time.strftime("%H:%M"),
        "total":      len(results),
        "lessons":    results,
    }


# ── 8. Full day ───────────────────────────────────────────────────────────────

@router.get("/day", summary="All lessons on a specific date across selected entities")
async def lessons_on_day(
    day:          date_type          = Query(..., description="YYYY-MM-DD"),
    entity_type:  Optional[str]      = Query(None, description="group | teacher | room"),
    institute_id: Optional[int]      = Query(None),
    subject:      Optional[str]      = Query(None),
    lesson_type:  Optional[str]      = Query(None),
    teacher_name: Optional[str]      = Query(None),
    room_name:    Optional[str]      = Query(None),
):
    date_iso = day.isoformat()
    results  = []

    async def scan(schedule: dict, etype: str, eid: int, ename: str):
        day_data = schedule.get(date_iso)
        if not day_data:
            return
        day_dict = _day_data_to_dict(day_data)
        for lesson in day_dict.get("lessons", []):
            if not _matches_lesson_filters(lesson, subject, lesson_type, teacher_name, room_name):
                continue
            results.append({
                "entity_type":  etype,
                "entity_id":    eid,
                "entity_name":  ename,
                "weekday_name": day_dict.get("weekday_name"),
                **lesson,
            })

    if entity_type in (None, "group"):
        q = {"schedule": {"$ne": {}}}
        if institute_id:
            q["institute_id"] = institute_id
        for g in await Group.find(q).to_list():
            await scan(g.schedule, "group", g.group_id, g.name)

    if entity_type in (None, "teacher"):
        for t in await Teacher.find({"schedule": {"$ne": {}}}).to_list():
            await scan(t.schedule, "teacher", t.teacher_id, t.full_name)

    if entity_type in (None, "room"):
        for r in await Room.find({"schedule": {"$ne": {}}}).to_list():
            await scan(r.schedule, "room", r.room_id, r.name)

    results.sort(key=lambda x: x.get("time_start", ""))
    return {
        "date":    date_iso,
        "total":   len(results),
        "lessons": results,
    }


# ── 9. Full week ──────────────────────────────────────────────────────────────

@router.get("/week", summary="All lessons in an ISO week across selected entities")
async def lessons_in_week(
    week:         int               = Query(..., ge=1, le=53, description="ISO week number"),
    year:         int               = Query(datetime.now().year, description="Year (defaults to current)"),
    entity_type:  Optional[str]     = Query(None, description="group | teacher | room"),
    institute_id: Optional[int]     = Query(None),
    subject:      Optional[str]     = Query(None),
    lesson_type:  Optional[str]     = Query(None),
):
    results: dict[str, list] = {}  # keyed by ISO date

    async def scan(schedule: dict, etype: str, eid: int, ename: str):
        for iso, day in _iter_schedule(schedule):
            day_dict = _day_data_to_dict(day)
            if day_dict.get("week_number") != week:
                continue
            try:
                if date_type.fromisoformat(iso).isocalendar()[0] != year:
                    continue
            except ValueError:
                continue
            for lesson in day_dict.get("lessons", []):
                if not _matches_lesson_filters(lesson, subject, lesson_type, None, None):
                    continue
                results.setdefault(iso, []).append({
                    "entity_type":  etype,
                    "entity_id":    eid,
                    "entity_name":  ename,
                    "weekday_name": day_dict.get("weekday_name"),
                    **lesson,
                })

    if entity_type in (None, "group"):
        q = {"schedule": {"$ne": {}}}
        if institute_id:
            q["institute_id"] = institute_id
        for g in await Group.find(q).to_list():
            await scan(g.schedule, "group", g.group_id, g.name)

    if entity_type in (None, "teacher"):
        for t in await Teacher.find({"schedule": {"$ne": {}}}).to_list():
            await scan(t.schedule, "teacher", t.teacher_id, t.full_name)

    if entity_type in (None, "room"):
        for r in await Room.find({"schedule": {"$ne": {}}}).to_list():
            await scan(r.schedule, "room", r.room_id, r.name)

    # Sort each day's lessons by time
    for iso in results:
        results[iso].sort(key=lambda x: x.get("time_start", ""))

    days = [{"date": iso, "lessons": lessons} for iso, lessons in sorted(results.items())]
    total = sum(len(d["lessons"]) for d in days)
    return {"week": week, "year": year, "total_lessons": total, "days": days}


# ── 10. Date range ────────────────────────────────────────────────────────────

@router.get("/range", summary="All lessons between two dates")
async def lessons_in_range(
    from_date:    date_type          = Query(...),
    to_date:      date_type          = Query(...),
    entity_type:  Optional[str]      = Query(None, description="group | teacher | room"),
    institute_id: Optional[int]      = Query(None),
    subject:      Optional[str]      = Query(None),
    lesson_type:  Optional[str]      = Query(None),
    teacher_name: Optional[str]      = Query(None),
    room_name:    Optional[str]      = Query(None),
    limit:        int                = Query(500, ge=1, le=5000),
):
    if (to_date - from_date).days > 90:
        raise HTTPException(status_code=400, detail="Range cannot exceed 90 days")

    from_iso, to_iso = from_date.isoformat(), to_date.isoformat()
    results = []

    async def scan(schedule: dict, etype: str, eid: int, ename: str):
        for iso, day in _iter_schedule(schedule):
            if iso < from_iso or iso > to_iso:
                continue
            day_dict = _day_data_to_dict(day)
            for lesson in day_dict.get("lessons", []):
                if not _matches_lesson_filters(lesson, subject, lesson_type, teacher_name, room_name):
                    continue
                results.append({
                    "entity_type":  etype,
                    "entity_id":    eid,
                    "entity_name":  ename,
                    "date":         iso,
                    "weekday_name": day_dict.get("weekday_name"),
                    **lesson,
                })
                if len(results) >= limit:
                    return

    if entity_type in (None, "group"):
        q = {"schedule": {"$ne": {}}}
        if institute_id:
            q["institute_id"] = institute_id
        for g in await Group.find(q).to_list():
            if len(results) < limit:
                await scan(g.schedule, "group", g.group_id, g.name)

    if entity_type in (None, "teacher") and len(results) < limit:
        for t in await Teacher.find({"schedule": {"$ne": {}}}).to_list():
            if len(results) < limit:
                await scan(t.schedule, "teacher", t.teacher_id, t.full_name)

    if entity_type in (None, "room") and len(results) < limit:
        for r in await Room.find({"schedule": {"$ne": {}}}).to_list():
            if len(results) < limit:
                await scan(r.schedule, "room", r.room_id, r.name)

    results.sort(key=lambda x: (x["date"], x.get("time_start", "")))
    return {
        "from_date": from_iso,
        "to_date":   to_iso,
        "total":     len(results),
        "lessons":   results,
    }


# ── 11. Next lesson(s) ────────────────────────────────────────────────────────

@router.get("/next", summary="Next upcoming lesson(s) for a teacher, room, or group")
async def next_lessons(
    teacher_id: Optional[int]  = Query(None),
    room_id:    Optional[int]  = Query(None),
    group_id:   Optional[int]  = Query(None),
    count:      int            = Query(1, ge=1, le=20, description="How many upcoming lessons to return"),
    from_dt:    Optional[datetime] = Query(None, description="Start from this datetime (default: now)"),
):
    if not any([teacher_id, room_id, group_id]):
        raise HTTPException(status_code=400, detail="Provide at least one of: teacher_id, room_id, group_id")

    base_dt   = from_dt or datetime.now()
    today_iso = base_dt.date().isoformat()
    now_time  = base_dt.time().replace(second=0, microsecond=0)

    upcoming = []

    async def collect(schedule: dict, etype: str, eid: int, ename: str):
        for iso, day in _iter_schedule(schedule):
            if iso < today_iso:
                continue
            day_dict = _day_data_to_dict(day)
            for lesson in day_dict.get("lessons", []):
                ts = lesson.get("time_start", "")
                # Same day: only include lessons that haven't ended yet
                if iso == today_iso:
                    try:
                        end_t = _parse_time(lesson.get("time_end", "00:00"))
                        if end_t < now_time:
                            continue
                    except Exception:
                        pass
                upcoming.append({
                    "entity_type":  etype,
                    "entity_id":    eid,
                    "entity_name":  ename,
                    "date":         iso,
                    "weekday_name": day_dict.get("weekday_name"),
                    **lesson,
                })

    if teacher_id:
        t = await Teacher.find_one(Teacher.teacher_id == teacher_id)
        if t and t.schedule:
            await collect(t.schedule, "teacher", t.teacher_id, t.full_name)

    if room_id:
        r = await Room.find_one(Room.room_id == room_id)
        if r and r.schedule:
            await collect(r.schedule, "room", r.room_id, r.name)

    if group_id:
        g = await Group.find_one(Group.group_id == group_id)
        if g and g.schedule:
            await collect(g.schedule, "group", g.group_id, g.name)

    upcoming.sort(key=lambda x: (x["date"], x.get("time_start", "")))

    return {
        "from":    base_dt.isoformat(),
        "count":   min(count, len(upcoming)),
        "lessons": upcoming[:count],
    }


# ── 12. Free rooms ────────────────────────────────────────────────────────────

@router.get("/free-rooms", summary="Rooms with no lessons at a given date and time")
async def free_rooms(
    dt:       datetime          = Query(..., description="ISO datetime e.g. 2026-03-10T10:00"),
    building: Optional[str]    = Query(None, description="Filter by building"),
    duration: int              = Query(90, ge=30, le=240, description="Duration in minutes to check availability"),
):
    date_iso   = dt.date().isoformat()
    start_time = dt.time().replace(second=0, microsecond=0)
    end_time   = (datetime.combine(dt.date(), start_time) + timedelta(minutes=duration)).time()

    room_q: dict = {}
    if building:
        room_q["building"] = {"$regex": building, "$options": "i"}

    all_rooms = await Room.find(room_q).sort("name").to_list()

    free = []
    busy = []

    for r in all_rooms:
        if not r.schedule:
            # No schedule data — mark as unknown
            continue

        day_data = r.schedule.get(date_iso)
        if not day_data:
            # No lessons this day at all
            free.append({"room_id": r.room_id, "name": r.name, "building": r.building})
            continue

        day_dict  = _day_data_to_dict(day_data)
        conflict  = False
        conflicts = []

        for lesson in day_dict.get("lessons", []):
            try:
                ls = _parse_time(lesson["time_start"])
                le = _parse_time(lesson["time_end"])
                # Overlap: requested start < lesson end AND requested end > lesson start
                if start_time < le and end_time > ls:
                    conflict = True
                    conflicts.append({
                        "time_start": lesson["time_start"],
                        "time_end":   lesson["time_end"],
                        "subject":    lesson.get("subject"),
                        "group":      lesson.get("teacher_name"),
                    })
            except Exception:
                pass

        if conflict:
            busy.append({
                "room_id":   r.room_id,
                "name":      r.name,
                "building":  r.building,
                "conflicts": conflicts,
            })
        else:
            free.append({"room_id": r.room_id, "name": r.name, "building": r.building})

    return {
        "datetime":    dt.isoformat(),
        "duration_min": duration,
        "free_count":  len(free),
        "busy_count":  len(busy),
        "free_rooms":  sorted(free, key=lambda x: x["name"]),
        "busy_rooms":  busy,
    }


# ── 13. Teacher → groups (with optional schedule) ────────────────────────────

@router.get("/teacher-groups", summary="Groups taught by a teacher, optionally with schedule")
async def teacher_groups(
    teacher_id:       int             = Query(...),
    with_schedule:    bool            = Query(False, description="Include schedule for each group"),
    from_date:        Optional[date_type] = Query(None),
    to_date:          Optional[date_type] = Query(None),
):
    teacher = await Teacher.find_one(Teacher.teacher_id == teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    groups = await Group.find({"group_id": {"$in": teacher.group_ids}}).sort("name").to_list()

    from_iso = from_date.isoformat() if from_date else None
    to_iso   = to_date.isoformat()   if to_date   else None

    result = []
    for g in groups:
        entry: dict = {
            "group_id":        g.group_id,
            "name":            g.name,
            "institute_name":  g.institute_name,
            "speciality_name": g.speciality_name,
            "course":          g.course,
        }
        if with_schedule and g.schedule:
            # Filter to only lessons taught by this teacher, optionally in date range
            filtered: dict[str, list] = {}
            for iso, day in _iter_schedule(g.schedule):
                if from_iso and iso < from_iso:
                    continue
                if to_iso and iso > to_iso:
                    continue
                day_dict = _day_data_to_dict(day)
                teacher_lessons = [
                    l for l in day_dict.get("lessons", [])
                    if l.get("teacher_id") == teacher_id
                ]
                if teacher_lessons:
                    filtered[iso] = teacher_lessons
            entry["schedule"] = filtered
        result.append(entry)

    return {
        "teacher_id":   teacher_id,
        "full_name":    teacher.full_name,
        "group_count":  len(result),
        "groups":       result,
    }


# ── 14. Conflict detection ────────────────────────────────────────────────────

@router.get("/conflicts", summary="Find scheduling conflicts (same teacher or room at the same time)")
async def find_conflicts(
    from_date:  date_type          = Query(...),
    to_date:    date_type          = Query(...),
    check_type: str                = Query("both", description="teacher | room | both"),
):
    if (to_date - from_date).days > 14:
        raise HTTPException(status_code=400, detail="Range cannot exceed 14 days for conflict check")

    from_iso, to_iso = from_date.isoformat(), to_date.isoformat()
    conflicts = []

    def find_time_conflicts(lessons: list[dict], context_id, context_name, context_type) -> list:
        found = []
        for i, a in enumerate(lessons):
            for b in lessons[i+1:]:
                try:
                    a_start = _parse_time(a["time_start"])
                    a_end   = _parse_time(a["time_end"])
                    b_start = _parse_time(b["time_start"])
                    b_end   = _parse_time(b["time_end"])
                    if a_start < b_end and a_end > b_start:
                        found.append({
                            "context_type": context_type,
                            "context_id":   context_id,
                            "context_name": context_name,
                            "lesson_a": a,
                            "lesson_b": b,
                        })
                except Exception:
                    pass
        return found

    if check_type in ("teacher", "both"):
        teachers = await Teacher.find({"schedule": {"$ne": {}}}).to_list()
        for t in teachers:
            for iso, day in _iter_schedule(t.schedule):
                if iso < from_iso or iso > to_iso:
                    continue
                day_dict = _day_data_to_dict(day)
                lessons  = day_dict.get("lessons", [])
                found = find_time_conflicts(lessons, t.teacher_id, t.full_name, "teacher")
                for c in found:
                    conflicts.append({"date": iso, **c})

    if check_type in ("room", "both"):
        rooms = await Room.find({"schedule": {"$ne": {}}}).to_list()
        for r in rooms:
            for iso, day in _iter_schedule(r.schedule):
                if iso < from_iso or iso > to_iso:
                    continue
                day_dict = _day_data_to_dict(day)
                lessons  = day_dict.get("lessons", [])
                found = find_time_conflicts(lessons, r.room_id, r.name, "room")
                for c in found:
                    conflicts.append({"date": iso, **c})

    conflicts.sort(key=lambda x: (x["date"], x.get("context_name", "")))
    return {
        "from_date":      from_iso,
        "to_date":        to_iso,
        "conflict_count": len(conflicts),
        "conflicts":      conflicts,
    }
