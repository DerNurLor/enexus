"""
GraphQL resolvers.
- All DB queries use MongoDB aggregation pipelines — never Python-side filtering.
- Redis-cached with ObjectId-safe serializer.
- Entities searchable by name OR id throughout.
- institute_id/institute_name propagated to every relevant type.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, AsyncGenerator
import asyncio
import orjson
from loguru import logger

from app.db.database import get_motor_db
from app.models.group import Group
from app.models.teacher import Teacher
from app.models.room import Room
from app.models.institute import Institute
from app.models.scrape_log import ScrapeLog
from app.cache.redis import cached, cache_key, hash_params, get_redis
from app.core.config import settings
from app.search.service import normalize_query, build_mongo_search

from .types import (
    LessonType, DayType,
    InstituteType, InstituteStats, SubjectStats, DayLoadStats,
    GroupType, GroupConnection,
    TeacherType, TeacherConnection,
    RoomType, RoomConnection,
    FreeRoomType, LessonConnection,
    SearchResult, OverviewType, ScrapeLogSummary,
    ScrapeResultType, ScheduleUpdatedEvent, PageInfo,
)

WEEKDAY_NAMES = {
    0: "Понедельник", 1: "Вторник",  2: "Среда",
    3: "Четверг",     4: "Пятница",  5: "Суббота", 6: "Воскресенье",
}


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# ── Type converters ───────────────────────────────────────────────────────────

def _lesson_from_doc(doc: dict) -> LessonType:
    d = doc.get("date")
    if isinstance(d, datetime):
        iso = d.date().isoformat()
    elif isinstance(d, date):
        iso = d.isoformat()
    else:
        iso = str(d)
    return LessonType(
        date=iso,
        time_start=doc.get("time_start", ""),
        time_end=doc.get("time_end", ""),
        week_number=doc.get("week_number", 0),
        academic_year=doc.get("academic_year", ""),
        subject=doc.get("subject", ""),
        lesson_type=doc.get("lesson_type"),
        subgroup=doc.get("subgroup"),
        week_type=doc.get("week_type"),
        note=doc.get("note"),
        group_id=doc.get("group_id", 0),
        group_name=doc.get("group_name", ""),
        institute_id=doc.get("institute_id"),
        institute_name=doc.get("institute_name"),
        teacher_id=doc.get("teacher_id"),
        teacher_name=doc.get("teacher_name"),
        room_id=doc.get("room_id"),
        room_name=doc.get("room_name"),
        building=doc.get("building"),
    )


def _group_type(g) -> GroupType:
    return GroupType(
        group_id=g.group_id, name=g.name,
        institute_id=g.institute_id, institute_name=g.institute_name,
        speciality_name=g.speciality_name, course=g.course,
        academic_year=g.academic_year, subjects=g.subjects or [],
        lessons_count=g.lessons_count, days_count=g.days_count,
        scrape_status=g.scrape_status,
        schedule_scraped_at=g.schedule_scraped_at.isoformat() if g.schedule_scraped_at else None,
    )


def _teacher_type(t) -> TeacherType:
    return TeacherType(
        teacher_id=t.teacher_id, full_name=t.full_name, short_name=t.short_name,
        institute_ids=t.institute_ids or [],
        institute_names=t.institute_names or [],
        subjects=t.subjects or [], lesson_types=t.lesson_types or [],
        group_names=t.group_names or [], lessons_count=t.lessons_count,
        scrape_status=t.scrape_status,
        schedule_scraped_at=t.schedule_scraped_at.isoformat() if t.schedule_scraped_at else None,
    )


def _room_type(r) -> RoomType:
    return RoomType(
        room_id=r.room_id, name=r.name, building=r.building, capacity=r.capacity,
        subjects=r.subjects or [], teacher_names=r.teacher_names or [],
        group_names=r.group_names or [], lessons_count=r.lessons_count,
        scrape_status=r.scrape_status,
        schedule_scraped_at=r.schedule_scraped_at.isoformat() if r.schedule_scraped_at else None,
    )


def _ser_lesson(d: dict) -> dict:
    """Strip non-serializable fields and normalise date for Redis cache."""
    out = {k: v for k, v in d.items() if k not in ("_id", "scraped_at")}
    dt = out.get("date")
    if isinstance(dt, datetime):
        out["date"] = dt.date().isoformat()
    elif isinstance(dt, date):
        out["date"] = dt.isoformat()
    return out


def _agg_days(raw: list) -> List[DayType]:
    """
    Convert aggregation $group results → DayType list.
    Handles three forms of _id:
      - datetime object  (fresh from MongoDB)
      - date object      (rare)
      - ISO string       (deserialized from Redis JSON cache, e.g. "2026-03-04T00:00:00")
    """
    result = []
    for day in sorted(raw, key=lambda x: str(x["_id"])):
        d = day["_id"]
        if isinstance(d, datetime):
            d_date = d.date()
        elif isinstance(d, date):
            d_date = d
        elif isinstance(d, str):
            try:
                d_date = date.fromisoformat(d[:10])
            except ValueError:
                continue
        else:
            continue
        wd   = d_date.weekday()
        wn   = day.get("week_number", d_date.isocalendar().week)
        lessons = sorted(day.get("lessons", []), key=lambda l: l.get("time_start", ""))
        result.append(DayType(
            date=d_date.isoformat(),
            weekday=wd,
            weekday_name=WEEKDAY_NAMES[wd],
            week_number=wn,
            lessons=[_lesson_from_doc(l) for l in lessons],
        ))
    return result


def _date_match(from_date: Optional[str], to_date: Optional[str], week: Optional[int]) -> dict:
    """Build the date/week part of a match stage. Default = today onwards (7 days)."""
    if week:
        return {"week_number": week}
    if from_date or to_date:
        df: dict = {}
        if from_date: df["$gte"] = datetime.combine(date.fromisoformat(from_date), datetime.min.time())
        if to_date:   df["$lte"] = datetime.combine(date.fromisoformat(to_date),   datetime.max.time())
        return {"date": df}
    # Default: from today for the next 7 days (not the whole current week from Monday)
    today  = date.today()
    end    = today + timedelta(days=6)
    return {"date": {
        "$gte": datetime.combine(today, datetime.min.time()),
        "$lte": datetime.combine(end,   datetime.max.time()),
    }}


# ── Institutes ────────────────────────────────────────────────────────────────

async def resolve_institutes(q: Optional[str] = None) -> List[InstituteType]:
    ck = cache_key("ncfu", "institutes", hash_params(q=q))

    async def _fetch():
        filters: dict = {}
        if q:
            nq = normalize_query(q).strip()
            # Generic words that mean "show everything" — don't filter
            _CATCHALL = {"институт", "институты", "филиал", "филиалы", "все", "all", "скфу", "ncfu"}
            if nq.lower() not in _CATCHALL:
                # Split into words and match any of them against name or short_name
                words = nq.split()
                word_clauses = []
                for word in words:
                    if len(word) >= 2:
                        word_clauses += [
                            {"name":       {"$regex": word, "$options": "i"}},
                            {"short_name": {"$regex": word, "$options": "i"}},
                        ]
                if word_clauses:
                    filters["$or"] = word_clauses
        institutes = await Institute.find(filters).sort("institute_id").to_list()
        result = []
        for inst in institutes:
            gc = await Group.find({"institute_id": inst.institute_id}).count()
            result.append({
                "institute_id": inst.institute_id,
                "short_name":   inst.short_name,
                "name":         inst.name,
                "branch_id":    inst.branch_id,
                "groups_count": gc,
            })
        return result

    data = await cached(ck, settings.cache_ttl_meta, _fetch)
    return [InstituteType(**d) for d in data]


# ── Groups ────────────────────────────────────────────────────────────────────

async def resolve_groups(
    q:            Optional[str] = None,
    institute_id: Optional[int] = None,
    institute_name: Optional[str] = None,
    course:       Optional[int] = None,
    first:        int = 50,
    after:        Optional[str] = None,
) -> GroupConnection:
    ck = cache_key("ncfu", "groups", hash_params(
        q=q, iid=institute_id, iname=institute_name, course=course, first=first, after=after
    ))

    async def _fetch():
        filters: dict = {}
        if q:
            nq = normalize_query(q)
            filters.update(build_mongo_search(nq, ["name"]))
        if institute_id:
            filters["institute_id"] = institute_id
        if institute_name:
            filters["institute_name"] = {"$regex": institute_name, "$options": "i"}
        if course:
            filters["course"] = course
        if after:
            filters["group_id"] = {"$gt": int(after)}

        groups = await Group.find(filters).sort("group_id").limit(first + 1).to_list()
        total  = await Group.find(filters).count()
        page   = groups[:first]
        return {
            "nodes":      [_group_type(g).__dict__ for g in page],
            "has_next":   len(groups) > first,
            "end_cursor": str(page[-1].group_id) if page else None,
            "total":      total,
        }

    data = await cached(ck, settings.cache_ttl_meta, _fetch)
    return GroupConnection(
        nodes=[GroupType(**n) for n in data["nodes"]],
        page_info=PageInfo(
            has_next_page=data["has_next"],
            end_cursor=data["end_cursor"],
            total_count=data["total"],
        ),
    )


async def resolve_group_schedule(
    group_id:   Optional[int]  = None,
    group_name: Optional[str]  = None,
    from_date:  Optional[str]  = None,
    to_date:    Optional[str]  = None,
    week:       Optional[int]  = None,
) -> List[DayType]:
    # Resolve group_id from name if needed
    gid = group_id
    if gid is None and group_name:
        # 1. Exact match
        g = await Group.find_one({"name": {"$regex": f"^{group_name}$", "$options": "i"}})
        # 2. Partial match
        if g is None:
            g = await Group.find_one({"name": {"$regex": group_name, "$options": "i"}})
        # 3. Normalized: replace spaces/underscores with dashes and try again
        if g is None:
            import re as _r
            norm = _r.sub(r'[\s_]+', '-', group_name.strip())
            if norm != group_name:
                g = await Group.find_one({"name": {"$regex": norm, "$options": "i"}})
        # 4. Reverse: try with dashes replaced by spaces
        if g is None:
            spaced = group_name.replace('-', ' ')
            g = await Group.find_one({"name": {"$regex": _r.escape(spaced), "$options": "i"}})
        # 5. Fuzzy: strip separators and match core letters+digits
        if g is None:
            import re as _r
            core = _r.sub(r'[\s\-_]', '', group_name.lower())
            # core[:4] strips dashes, but DB names have dashes so regex must use prefix before dash
            # Use the first letters-only segment (up to 4 chars) of the original name for pre-filter
            prefix = _r.match(r'^([а-яёa-z]+)', group_name.lower())
            prefix_str = prefix.group(1)[:6] if prefix else core[:4]
            candidates = await Group.find({
                "name": {"$regex": prefix_str, "$options": "i"}
            }).to_list(100)
            if candidates:
                from rapidfuzz import process as fz, fuzz as fzf
                # Strip dashes from BOTH sides for fair comparison
                norm_map = {_r.sub(r'[\s\-_]', '', c.name.lower()): c for c in candidates}
                best = fz.extractOne(core, list(norm_map.keys()), scorer=fzf.WRatio)
                if best and best[1] >= 65:
                    g = norm_map[best[0]]
        gid = g.group_id if g else None
    if gid is None:
        return []

    match: dict = {"group_id": gid, **_date_match(from_date, to_date, week)}
    ck = cache_key("ncfu", "gs", gid, hash_params(f=from_date, t=to_date, w=week))

    async def _fetch():
        col = get_motor_db()["lessons"]
        pipeline = [
            {"$match": match},
            {"$sort":  {"date": 1, "time_start": 1}},
            {"$group": {"_id": "$date", "week_number": {"$first": "$week_number"},
                        "lessons": {"$push": "$$ROOT"}}},
            {"$sort":  {"_id": 1}},
        ]
        return await col.aggregate(pipeline).to_list(length=None)

    return _agg_days(await cached(ck, settings.cache_ttl_day, _fetch))


# ── Teachers ──────────────────────────────────────────────────────────────────

async def resolve_teachers(
    q:            Optional[str] = None,
    subject:      Optional[str] = None,
    institute_id: Optional[int] = None,
    institute_name: Optional[str] = None,
    first:        int = 50,
    after:        Optional[str] = None,
) -> TeacherConnection:
    ck = cache_key("ncfu", "teachers", hash_params(
        q=q, sub=subject, iid=institute_id, iname=institute_name, first=first, after=after
    ))

    async def _fetch():
        filters: dict = {}
        if q:
            nq = normalize_query(q)
            filters.update(build_mongo_search(nq, ["full_name"]))
        if subject:
            filters["subjects"] = {"$regex": subject, "$options": "i"}
        if institute_id:
            filters["institute_ids"] = institute_id
        if institute_name:
            filters["institute_names"] = {"$regex": institute_name, "$options": "i"}
        if after:
            filters["teacher_id"] = {"$gt": int(after)}

        teachers = await Teacher.find(filters).sort("teacher_id").limit(first + 1).to_list()
        total    = await Teacher.find(filters).count()
        page     = teachers[:first]
        return {
            "nodes":      [_teacher_type(t).__dict__ for t in page],
            "has_next":   len(teachers) > first,
            "end_cursor": str(page[-1].teacher_id) if page else None,
            "total":      total,
        }

    data = await cached(ck, settings.cache_ttl_meta, _fetch)
    return TeacherConnection(
        nodes=[TeacherType(**n) for n in data["nodes"]],
        page_info=PageInfo(
            has_next_page=data["has_next"],
            end_cursor=data["end_cursor"],
            total_count=data["total"],
        ),
    )


async def resolve_teacher_schedule(
    teacher_id:   Optional[int] = None,
    teacher_name: Optional[str] = None,
    from_date:    Optional[str] = None,
    to_date:      Optional[str] = None,
    week:         Optional[int] = None,
) -> List[DayType]:
    tid = teacher_id
    if tid is None and teacher_name:
        import re as _r
        # 1. Exact match in full_name or short_name
        t = await Teacher.find_one({"full_name": {"$regex": teacher_name, "$options": "i"}})
        if t is None:
            t = await Teacher.find_one({"short_name": {"$regex": teacher_name, "$options": "i"}})
        # 2. Fuzzy match to handle oblique grammatical cases
        # Extract the surname (first word or whole string if one word)
        if t is None:
            surname_raw = teacher_name.strip().split()[0] if teacher_name.strip() else teacher_name
            # Strip last 1-3 chars progressively to cover case endings
            # e.g. "Щербины" → try "Щербин", "Щербины", etc.
            prefixes_to_try = []
            for trim in range(0, 4):
                p = surname_raw[:-trim] if trim > 0 else surname_raw
                if len(p) >= 3 and p not in prefixes_to_try:
                    prefixes_to_try.append(p)

            for prefix in prefixes_to_try:
                candidates = await Teacher.find(
                    {"full_name": {"$regex": prefix, "$options": "i"}}
                ).to_list(20)
                if candidates:
                    if len(candidates) == 1:
                        t = candidates[0]
                        break
                    # Use rapidfuzz to pick the best match
                    try:
                        from rapidfuzz import process as fz, fuzz as fzf
                        norm_q = _r.sub(r'[\s\-_]', '', teacher_name.lower())
                        norm_map = {_r.sub(r'[\s\-_]', '', c.full_name.lower()): c for c in candidates}
                        best = fz.extractOne(norm_q, list(norm_map.keys()), scorer=fzf.WRatio)
                        if best and best[1] >= 55:
                            t = norm_map[best[0]]
                            break
                    except ImportError:
                        t = candidates[0]
                        break
        tid = t.teacher_id if t else None
    if tid is None:
        return []

    match: dict = {"teacher_id": tid, **_date_match(from_date, to_date, week)}
    ck = cache_key("ncfu", "ts", tid, hash_params(f=from_date, t=to_date, w=week))

    async def _fetch():
        col = get_motor_db()["lessons"]
        pipeline = [
            {"$match": match},
            {"$sort":  {"date": 1, "time_start": 1}},
            {"$group": {"_id": "$date", "week_number": {"$first": "$week_number"},
                        "lessons": {"$push": "$$ROOT"}}},
            {"$sort":  {"_id": 1}},
        ]
        return await col.aggregate(pipeline).to_list(length=None)

    return _agg_days(await cached(ck, settings.cache_ttl_day, _fetch))


# ── Rooms ─────────────────────────────────────────────────────────────────────

async def resolve_rooms(
    q:        Optional[str] = None,
    building: Optional[str] = None,
    first:    int = 50,
    after:    Optional[str] = None,
) -> RoomConnection:
    ck = cache_key("ncfu", "rooms", hash_params(q=q, b=building, first=first, after=after))

    async def _fetch():
        filters: dict = {}
        if q:
            nq = normalize_query(q)
            filters.update(build_mongo_search(nq, ["name"]))
        if building:
            filters["building"] = {"$regex": building, "$options": "i"}
        if after:
            filters["room_id"] = {"$gt": int(after)}

        rooms = await Room.find(filters).sort("room_id").limit(first + 1).to_list()
        total = await Room.find(filters).count()
        page  = rooms[:first]
        return {
            "nodes":      [_room_type(r).__dict__ for r in page],
            "has_next":   len(rooms) > first,
            "end_cursor": str(page[-1].room_id) if page else None,
            "total":      total,
        }

    data = await cached(ck, settings.cache_ttl_meta, _fetch)
    return RoomConnection(
        nodes=[RoomType(**n) for n in data["nodes"]],
        page_info=PageInfo(
            has_next_page=data["has_next"],
            end_cursor=data["end_cursor"],
            total_count=data["total"],
        ),
    )


async def resolve_room_schedule(
    room_id:   Optional[int] = None,
    room_name: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date:   Optional[str] = None,
    week:      Optional[int] = None,
) -> List[DayType]:
    rid = room_id
    if rid is None and room_name:
        import re as _r
        rn = room_name.strip()

        # ── Gym / sport hall detection ───────────────────────────────────────
        # Covers: "спортзал", "спорт зал", "с/з", "с.з", "сз", "gym"
        # and building-prefixed variants: "9-с/з", "9 спортзал", "корпус 9 с/з"
        _GYM_RE = _r.compile(
            r'спортивный\s*зал|спортзал|спорт\s*зал|с/з|с\.з\.?|^сз$|gym',
            _r.IGNORECASE,
        )
        _GYM_WITH_BLDG_RE = _r.compile(
            r'^(?:корпус\s*)?(\d{1,2})\s*[-–\s]\s*'
            r'(?:спортивный\s*зал|спортзал|спорт\s*зал|с/з|с\.з\.?|сз|gym)',
            _r.IGNORECASE,
        )
        bldg_gym = _GYM_WITH_BLDG_RE.match(rn)
        is_gym   = bool(bldg_gym) or bool(_GYM_RE.search(rn))

        if is_gym:
            gym_filter = {"$or": [
                {"name": {"$regex": r"с/з",       "$options": "i"}},
                {"name": {"$regex": r"с\.з",       "$options": "i"}},
                {"name": {"$regex": r"^сз$",       "$options": "i"}},
                {"name": {"$regex": r"спортзал",   "$options": "i"}},
                {"name": {"$regex": r"спорт.*зал", "$options": "i"}},
            ]}
            if bldg_gym:
                bnum = bldg_gym.group(1)
                gym_filter = {"$and": [
                    gym_filter,
                    {"$or": [
                        {"building": {"$regex": _r.escape(bnum), "$options": "i"}},
                        {"name":     {"$regex": f"^{_r.escape(bnum)}[-–]", "$options": "i"}},
                    ]},
                ]}
            r_obj = await Room.find_one(gym_filter)
            if r_obj:
                rid = r_obj.room_id

        if rid is None:
            # "11-405" or "11-216" → building=11, room=405
            dash_m    = _r.match(r'^(\d{1,2})-(\d{3,})$', rn)
            space_m   = _r.match(r'^(\d{1,2})\s+(\d{3,})$', rn)
            bldg_kw_m = _r.match(r'(?:корпус\s*)?(\d{1,2})[\s,\-]+(\d{3,})', rn, _r.IGNORECASE)

            bldg, rnum = None, None
            if dash_m:
                bldg, rnum = dash_m.group(1), dash_m.group(2)
            elif space_m:
                bldg, rnum = space_m.group(1), space_m.group(2)
            elif bldg_kw_m:
                bldg, rnum = bldg_kw_m.group(1), bldg_kw_m.group(2)

            if bldg and rnum:
                r_obj = await Room.find_one({
                    "name":     {"$regex": _r.escape(rnum), "$options": "i"},
                    "building": {"$regex": _r.escape(bldg), "$options": "i"},
                })
                if r_obj is None:
                    r_obj = await Room.find_one({
                        "name": {"$regex": _r.escape(f"{bldg}-{rnum}"), "$options": "i"}
                    })
                if r_obj is None:
                    r_obj = await Room.find_one({
                        "name": {"$regex": _r.escape(rnum), "$options": "i"}
                    })
                if r_obj:
                    rid = r_obj.room_id

        if rid is None:
            # "11 407" (number + text room name)
            bldg_m = _r.match(r'^(\d+)\s+(.+)$', rn)
            if bldg_m:
                bldg2, rname2 = bldg_m.group(1), bldg_m.group(2)
                r_obj = await Room.find_one({
                    "name":     {"$regex": _r.escape(rname2), "$options": "i"},
                    "building": {"$regex": _r.escape(bldg2), "$options": "i"},
                })
                if r_obj:
                    rid = r_obj.room_id

        if rid is None:
            r_obj = await Room.find_one({"name": {"$regex": f"^{_r.escape(rn)}$", "$options": "i"}})
            if r_obj is None:
                r_obj = await Room.find_one({"name": {"$regex": _r.escape(rn), "$options": "i"}})
            rid = r_obj.room_id if r_obj else None
    if rid is None:
        return []

    match: dict = {"room_id": rid, **_date_match(from_date, to_date, week)}
    ck = cache_key("ncfu", "rs", rid, hash_params(f=from_date, t=to_date, w=week))

    async def _fetch():
        col = get_motor_db()["lessons"]
        pipeline = [
            {"$match": match},
            {"$sort":  {"date": 1, "time_start": 1}},
            {"$group": {"_id": "$date", "week_number": {"$first": "$week_number"},
                        "lessons": {"$push": "$$ROOT"}}},
            {"$sort":  {"_id": 1}},
        ]
        return await col.aggregate(pipeline).to_list(length=None)

    return _agg_days(await cached(ck, settings.cache_ttl_day, _fetch))


# ── Now ───────────────────────────────────────────────────────────────────────

async def resolve_now() -> List[LessonType]:
    ck = cache_key("ncfu", "now", datetime.utcnow().strftime("%Y%m%d%H%M"))

    async def _fetch():
        col = get_motor_db()["lessons"]
        now_time = datetime.utcnow().strftime("%H:%M")
        today_dt = datetime.combine(date.today(), datetime.min.time())
        pipeline = [
            {"$match": {
                "date":       today_dt,
                "time_start": {"$lte": now_time},
                "time_end":   {"$gte": now_time},
            }},
            {"$sort": {"time_start": 1}},
            {"$limit": 500},
        ]
        docs = await col.aggregate(pipeline).to_list(length=None)
        return [_ser_lesson(d) for d in docs]

    data = await cached(ck, settings.cache_ttl_now, _fetch)
    return [_lesson_from_doc(d) for d in data]


# ── Lessons on a day ──────────────────────────────────────────────────────────

async def resolve_lessons_on_day(
    day:                str,
    group_id:           Optional[int] = None,
    group_name:         Optional[str] = None,
    teacher_id:         Optional[int] = None,
    teacher_name:       Optional[str] = None,
    room_id:            Optional[int] = None,
    room_name:          Optional[str] = None,
    institute_id:       Optional[int] = None,
    institute_name:     Optional[str] = None,
    subject:            Optional[str] = None,
    lesson_type_filter: Optional[str] = None,
    first:              int = 200,
) -> LessonConnection:
    # Resolve name → id when only name provided
    if group_id is None and group_name:
        g = await Group.find_one({"name": {"$regex": group_name, "$options": "i"}})
        group_id = g.group_id if g else None
    if teacher_id is None and teacher_name:
        import re as _r2
        t = await Teacher.find_one({"full_name": {"$regex": teacher_name, "$options": "i"}})
        if t is None:
            t = await Teacher.find_one({"short_name": {"$regex": teacher_name, "$options": "i"}})
        if t is None:
            # Fuzzy fallback for oblique case forms
            surname_raw = teacher_name.strip().split()[0] if teacher_name.strip() else teacher_name
            for trim in range(0, 4):
                prefix = surname_raw[:-trim] if trim > 0 else surname_raw
                if len(prefix) < 3:
                    break
                candidates = await Teacher.find(
                    {"full_name": {"$regex": prefix, "$options": "i"}}
                ).to_list(20)
                if candidates:
                    try:
                        from rapidfuzz import process as fz2, fuzz as fzf2
                        norm_q2 = _r2.sub(r'[\s\-_]', '', teacher_name.lower())
                        norm_map2 = {_r2.sub(r'[\s\-_]', '', c.full_name.lower()): c for c in candidates}
                        best2 = fz2.extractOne(norm_q2, list(norm_map2.keys()), scorer=fzf2.WRatio)
                        if best2 and best2[1] >= 55:
                            t = norm_map2[best2[0]]
                            break
                    except ImportError:
                        t = candidates[0]
                        break
        teacher_id = t.teacher_id if t else None
    if room_id is None and room_name:
        r = await Room.find_one({"name": {"$regex": room_name, "$options": "i"}})
        room_id = r.room_id if r else None

    ck = cache_key("ncfu", "day", hash_params(
        day=day, gid=group_id, tid=teacher_id, rid=room_id,
        iid=institute_id, iname=institute_name, sub=subject, lt=lesson_type_filter, first=first,
    ))

    async def _fetch():
        col   = get_motor_db()["lessons"]
        d_dt  = datetime.combine(date.fromisoformat(day), datetime.min.time())
        match: dict = {"date": d_dt}
        if group_id:        match["group_id"]      = group_id
        if teacher_id:      match["teacher_id"]    = teacher_id
        if room_id:         match["room_id"]        = room_id
        if institute_id:    match["institute_id"]  = institute_id
        if institute_name:  match["institute_name"] = {"$regex": institute_name, "$options": "i"}
        if subject:         match["subject"]        = {"$regex": subject,            "$options": "i"}
        if lesson_type_filter:
                            match["lesson_type"]    = {"$regex": lesson_type_filter, "$options": "i"}
        total = await col.count_documents(match)
        docs  = await col.find(match).sort("time_start", 1).limit(first).to_list(length=None)
        return {"docs": [_ser_lesson(d) for d in docs], "total": total}

    data = await cached(ck, settings.cache_ttl_day, _fetch)
    lessons = [_lesson_from_doc(d) for d in data["docs"]]
    return LessonConnection(
        nodes=lessons,
        page_info=PageInfo(
            has_next_page=len(lessons) == first,
            end_cursor=None,
            total_count=data["total"],
        ),
    )


# ── Free rooms ────────────────────────────────────────────────────────────────

async def resolve_free_rooms(
    at:               str,
    duration_minutes: int          = 90,
    building:         Optional[str] = None,
    institute_id:     Optional[int] = None,
) -> List[FreeRoomType]:
    ck = cache_key("ncfu", "free", hash_params(at=at, dur=duration_minutes, b=building, iid=institute_id))

    async def _fetch():
        col         = get_motor_db()["lessons"]
        dt          = datetime.fromisoformat(at)
        check_end   = (dt + timedelta(minutes=duration_minutes)).strftime("%H:%M")
        check_start = dt.strftime("%H:%M")
        today_dt    = datetime.combine(dt.date(), datetime.min.time())

        # Занятые аудитории — фильтруем по институту если задан,
        # чтобы не считать занятыми одноимённые аудитории других филиалов.
        busy_filter: dict = {
            "date":       today_dt,
            "room_id":    {"$ne": None},
            "time_start": {"$lt": check_end},
            "time_end":   {"$gt": check_start},
        }
        if institute_id:
            busy_filter["institute_id"] = institute_id

        busy_ids = set(await col.distinct("room_id", busy_filter))

        room_filter: dict = {"room_id": {"$nin": list(busy_ids)}}
        if building:
            b = building.strip()
            import re as _re
            num = _re.sub(r'(?i)корпус\s*', '', b).strip()
            if num:
                room_filter["building"] = {"$regex": num, "$options": "i"}
            else:
                room_filter["building"] = {"$regex": b, "$options": "i"}
        if institute_id:
            room_filter["institute_ids"] = institute_id

        rooms = await Room.find(room_filter).sort("name").to_list()
        return [{"room_id": r.room_id, "name": r.name,
                 "building": r.building, "capacity": r.capacity} for r in rooms]

    data = await cached(ck, 60, _fetch)
    return [FreeRoomType(**r) for r in data]


# ── Universal search ──────────────────────────────────────────────────────────

async def resolve_search(
    q:            str,
    institute_id: Optional[int] = None,
) -> SearchResult:
    nq = normalize_query(q)
    ck = cache_key("ncfu", "search", hash_params(q=nq, iid=institute_id))

    async def _fetch():
        g_f: dict = build_mongo_search(nq, ["name"])
        t_f: dict = build_mongo_search(nq, ["full_name"])
        r_f: dict = build_mongo_search(nq, ["name"])
        if institute_id:
            g_f["institute_id"]   = institute_id
            t_f["institute_ids"]  = institute_id
            r_f["institute_ids"]  = institute_id  # аудитории тоже фильтруем по институту

        groups   = await Group.find(g_f).limit(15).to_list()
        teachers = await Teacher.find(t_f).limit(15).to_list()
        rooms    = await Room.find(r_f).limit(15).to_list()

        # ── Fuzzy surname fallback for teachers (handles oblique cases) ──────
        if not teachers and len(nq) >= 3:
            import re as _r
            # Try progressively shorter prefixes (handle genitive/dative endings)
            surname_raw = nq.strip().split()[0]
            for trim in range(0, 4):
                prefix = surname_raw[:-trim] if trim > 0 else surname_raw
                if len(prefix) < 3:
                    break
                cands = await Teacher.find(
                    {"full_name": {"$regex": prefix, "$options": "i"}}
                ).limit(15).to_list()
                if cands:
                    teachers = cands
                    break

        return {
            "groups":   [_group_type(g).__dict__   for g in groups],
            "teachers": [_teacher_type(t).__dict__ for t in teachers],
            "rooms":    [_room_type(r).__dict__    for r in rooms],
        }

    data = await cached(ck, settings.cache_ttl_search, _fetch)
    return SearchResult(
        groups=[GroupType(**g)     for g in data["groups"]],
        teachers=[TeacherType(**t) for t in data["teachers"]],
        rooms=[RoomType(**r)       for r in data["rooms"]],
        data_as_of=_now_iso(),
    )


# ── Overview ──────────────────────────────────────────────────────────────────

async def resolve_overview(recent_scrapes_limit: int = 5) -> OverviewType:
    ck = cache_key("ncfu", "overview", recent_scrapes_limit)

    async def _fetch():
        db  = get_motor_db()
        col = db["lessons"]

        # Basic counts
        g_total = await Group.count()
        t_total = await Teacher.count()
        r_total = await Room.count()
        l_total = await col.count_documents({})
        i_total = await Institute.count()

        # Recent scrape logs
        logs = await ScrapeLog.find_all().sort("-started_at").limit(recent_scrapes_limit).to_list()
        lg   = logs[0] if logs else None
        duration = None
        if lg and lg.finished_at:
            duration = (lg.finished_at - lg.started_at).total_seconds()

        def _log_dict(log) -> dict:
            dur = None
            if log.finished_at:
                dur = (log.finished_at - log.started_at).total_seconds()
            return {
                "id": str(log.id),
                "started_at":        log.started_at.isoformat(),
                "finished_at":       log.finished_at.isoformat() if log.finished_at else None,
                "status":            log.status,
                "mode":              log.mode,
                "groups_total":      log.groups_total,
                "groups_scraped":    log.groups_scraped,
                "groups_failed":     log.groups_failed,
                "lessons_written":   log.lessons_written,
                "lessons_unchanged": log.lessons_unchanged,
                "teachers_upserted": log.teachers_upserted,
                "rooms_upserted":    log.rooms_upserted,
                "errors":            log.errors,
                "triggered_by":      log.triggered_by,
                "duration_seconds":  dur,
            }

        # Per-institute breakdown
        institute_pipeline = [
            {"$group": {
                "_id":          "$institute_id",
                "institute_name": {"$first": "$institute_name"},
                "groups_count": {"$addToSet": "$group_id"},
                "lessons_count": {"$sum": 1},
            }},
            {"$sort": {"lessons_count": -1}},
            {"$limit": 20},
        ]
        inst_raw = await col.aggregate(institute_pipeline).to_list(length=None)
        institutes = await Institute.find_all().to_list()
        inst_map   = {i.institute_id: i.short_name for i in institutes}
        # Teacher counts per institute
        t_pipeline = [
            {"$unwind": "$institute_ids"},
            {"$group": {"_id": "$institute_ids", "count": {"$sum": 1}}},
        ]
        t_raw      = await db["teachers"].aggregate(t_pipeline).to_list(length=None)
        t_by_inst  = {d["_id"]: d["count"] for d in t_raw}

        by_institute = [
            {
                "institute_id":   d["_id"],
                "institute_name": d.get("institute_name") or "",
                "short_name":     inst_map.get(d["_id"], ""),
                "groups_count":   len(d["groups_count"]),
                "teachers_count": t_by_inst.get(d["_id"], 0),
                "lessons_count":  d["lessons_count"],
            }
            for d in inst_raw if d["_id"]
        ]

        # Top subjects
        subj_pipeline = [
            {"$group": {
                "_id": "$subject",
                "lessons_count":  {"$sum": 1},
                "groups_count":   {"$addToSet": "$group_id"},
                "teachers_count": {"$addToSet": "$teacher_id"},
            }},
            {"$sort": {"lessons_count": -1}},
            {"$limit": 10},
        ]
        subj_raw    = await col.aggregate(subj_pipeline).to_list(length=None)
        top_subjects = [
            {
                "subject":        d["_id"] or "—",
                "lessons_count":  d["lessons_count"],
                "groups_count":   len(d["groups_count"]),
                "teachers_count": len([x for x in d["teachers_count"] if x]),
            }
            for d in subj_raw
        ]

        # Upcoming 7 days load
        today    = date.today()
        today_dt = datetime.combine(today, datetime.min.time())
        week_end = datetime.combine(today + timedelta(days=7), datetime.max.time())
        day_pipeline = [
            {"$match": {"date": {"$gte": today_dt, "$lte": week_end}}},
            {"$group": {
                "_id":          "$date",
                "lessons_count": {"$sum": 1},
                "groups_active": {"$addToSet": "$group_id"},
            }},
            {"$sort": {"_id": 1}},
        ]
        day_raw = await col.aggregate(day_pipeline).to_list(length=None)
        upcoming_days = []
        for d in day_raw:
            raw_d = d["_id"]
            if isinstance(raw_d, datetime):
                day_date = raw_d.date()
            else:
                day_date = raw_d
            wd = day_date.weekday()
            upcoming_days.append({
                "date":          day_date.isoformat(),
                "weekday_name":  WEEKDAY_NAMES[wd],
                "lessons_count": d["lessons_count"],
                "groups_active": len(d["groups_active"]),
            })

        return {
            "groups_total":         g_total,
            "teachers_total":       t_total,
            "rooms_total":          r_total,
            "lessons_total":        l_total,
            "institutes_total":     i_total,
            "last_scrape_at":       lg.started_at.isoformat() if lg else None,
            "last_scrape_status":   lg.status if lg else None,
            "last_scrape_mode":     lg.mode if lg else None,
            "last_scrape_duration": duration,
            "lessons_written_last": lg.lessons_written if lg else None,
            "groups_failed_last":   lg.groups_failed if lg else None,
            "recent_scrapes":       [_log_dict(l) for l in logs],
            "by_institute":         by_institute,
            "top_subjects":         top_subjects,
            "upcoming_days":        upcoming_days,
        }

    data = await cached(ck, settings.cache_ttl_overview, _fetch)
    return OverviewType(
        **{k: v for k, v in data.items() if k not in
           ("recent_scrapes", "by_institute", "top_subjects", "upcoming_days")},
        recent_scrapes=[ScrapeLogSummary(**s) for s in data["recent_scrapes"]],
        by_institute=[InstituteStats(**s)     for s in data["by_institute"]],
        top_subjects=[SubjectStats(**s)       for s in data["top_subjects"]],
        upcoming_days=[DayLoadStats(**s)      for s in data["upcoming_days"]],
        data_as_of=_now_iso(),
    )


# ── Scrape trigger ────────────────────────────────────────────────────────────

async def resolve_trigger_scrape(mode: str = "incremental") -> ScrapeResultType:
    # Scrape trigger не доступен в miniapp-сервисе — только в backend
    return ScrapeResultType(status="unavailable", mode=mode, triggered_at=_now_iso())


# ── Subscription ──────────────────────────────────────────────────────────────

async def subscribe_schedule_updated(
    group_id: Optional[int] = None,
) -> AsyncGenerator[ScheduleUpdatedEvent, None]:
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe("ncfu:schedule_updated")
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = orjson.loads(message["data"])
            except Exception:
                continue
            if group_id and data.get("group_id") != group_id:
                continue
            yield ScheduleUpdatedEvent(
                group_id=data["group_id"],
                group_name=data.get("group_name", ""),
                changed_dates=data.get("changed_dates", []),
                data_as_of=_now_iso(),
            )
    finally:
        await pubsub.unsubscribe("ncfu:schedule_updated")

# Alias: schema.py calls resolve_lessons_on, resolver is resolve_lessons_on_day
resolve_lessons_on = resolve_lessons_on_day
