"""
backend/app/api/routes/campuses.py

REST API для объектов кампуса СКФУ.

Эндпоинты:
  GET  /campuses/             — список всех объектов (с фильтрацией)
  GET  /campuses/cities       — список городов с количеством объектов
  GET  /campuses/{source_id}  — один объект по id
  POST /campuses/sync         — ручная синхронизация из API (admin)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from loguru import logger

from app.models.campus import Campus

router = APIRouter(prefix="/campuses", tags=["Campuses"])

# ── Кеш последней синхронизации (in-memory, достаточно) ──────────────────────
_last_sync: datetime | None = None


# ── Сериализатор ──────────────────────────────────────────────────────────────

def _serialize(c: Campus) -> dict:
    return {
        "id":           str(c.id),
        "source_id":    c.source_id,
        "city_id":      c.city_id,
        "city_title":   c.city_title,
        "title":        c.title,
        "full_title":   c.full_title,
        "address":      c.address,
        "photo":        c.photo,
        "lat":          c.lat,
        "lon":          c.lon,
        "transport": {
            "bus":        c.transport.bus,
            "trolleybus": c.transport.trolleybus,
            "tram":       c.transport.tram,
        },
        "type": {
            "id":    c.type.id,
            "title": c.type.title,
        },
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


# ── GET /campuses/ ─────────────────────────────────────────────────────────────

@router.get(
    "/",
    summary="Список объектов кампуса",
    description="""
Возвращает объекты кампуса СКФУ с опциональной фильтрацией.

Параметры:
- **city_id**: id города (838=Ставрополь, 832=Пятигорск, 826=Невинномысск)
- **type_id**: тип (campuses | hostels | cafe | banks | misc)
- **q**: поиск по названию или адресу (case-insensitive)
- **with_coords**: только объекты с координатами (default: true)
""",
)
async def list_campuses(
    city_id:     Optional[str] = Query(None, description="ID города"),
    type_id:     Optional[str] = Query(None, description="Тип объекта"),
    q:           Optional[str] = Query(None, description="Поиск по названию / адресу"),
    with_coords: bool          = Query(True,  description="Только с координатами"),
    limit:       int           = Query(200,   ge=1, le=500),
):
    flt: dict = {}

    if city_id:
        flt["city_id"] = city_id
    if type_id:
        flt["type.id"] = type_id
    if with_coords:
        flt["lat"]  = {"$ne": None}
        flt["lon"]  = {"$ne": None}
    if q:
        import re
        pattern = re.escape(q.strip())
        flt["$or"] = [
            {"full_title": {"$regex": pattern, "$options": "i"}},
            {"address":    {"$regex": pattern, "$options": "i"}},
        ]

    items = await Campus.find(flt).limit(limit).to_list()
    return {
        "items":  [_serialize(c) for c in items],
        "total":  len(items),
        "filter": {
            "city_id": city_id,
            "type_id": type_id,
            "q":       q,
        },
    }


# ── GET /campuses/cities ───────────────────────────────────────────────────────

@router.get(
    "/cities",
    summary="Города с количеством объектов",
)
async def list_cities():
    """
    Возвращает список городов с общим количеством объектов и
    разбивкой по типам. Используется фронтом для вкладок-переключателей.
    """
    # Агрегация: group by city_id
    pipeline = [
        {
            "$group": {
                "_id":       "$city_id",
                "title":     {"$first": "$city_title"},
                "total":     {"$sum": 1},
                "campuses":  {"$sum": {"$cond": [{"$eq": ["$type.id", "campuses"]}, 1, 0]}},
                "hostels":   {"$sum": {"$cond": [{"$eq": ["$type.id", "hostels"]},  1, 0]}},
                "cafe":      {"$sum": {"$cond": [{"$eq": ["$type.id", "cafe"]},     1, 0]}},
                "banks":     {"$sum": {"$cond": [{"$eq": ["$type.id", "banks"]},    1, 0]}},
                "misc":      {"$sum": {"$cond": [{"$eq": ["$type.id", "misc"]},     1, 0]}},
            }
        },
        {"$sort": {"total": -1}},
    ]
    motor_col = Campus.get_motor_collection()
    raw = await motor_col.aggregate(pipeline).to_list(length=20)

    cities = []
    for row in raw:
        cities.append({
            "id":       row["_id"],
            "title":    row["title"],
            "total":    row["total"],
            "by_type": {
                "campuses": row["campuses"],
                "hostels":  row["hostels"],
                "cafe":     row["cafe"],
                "banks":    row["banks"],
                "misc":     row["misc"],
            },
        })

    return {"cities": cities}


# ── GET /campuses/{source_id} ──────────────────────────────────────────────────

@router.get(
    "/{source_id}",
    summary="Один объект по source_id",
)
async def get_campus(source_id: str):
    campus = await Campus.find_one(Campus.source_id == source_id)
    if not campus:
        raise HTTPException(status_code=404, detail=f"Campus '{source_id}' not found")
    return _serialize(campus)


# ── POST /campuses/sync ────────────────────────────────────────────────────────

@router.post(
    "/sync",
    summary="Синхронизировать данные из API СКФУ (admin)",
)
async def sync_campuses_manual(
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Принудительно, даже если синхронизация недавно запускалась"),
):
    """
    Ручной запуск синхронизации данных кампусов из https://ncfu.ru/api/campuses/list.php.

    Требует роль admin (проверка через X-Admin-Secret или JWT — добавьте Depends по вашей архитектуре).
    По умолчанию запускается в фоне и сразу возвращает 202.
    """
    global _last_sync

    # Защита от слишком частого запуска
    if not force and _last_sync:
        elapsed = (datetime.now(timezone.utc) - _last_sync).total_seconds()
        if elapsed < 300:
            return {
                "status":  "skipped",
                "reason":  "too_soon",
                "elapsed_seconds": int(elapsed),
                "next_allowed_in": int(300 - elapsed),
            }

    async def _run():
        global _last_sync
        _last_sync = datetime.now(timezone.utc)
        try:
            from app.scraper.campus_scraper import sync_campuses
            result = await sync_campuses()
            logger.info(f"Manual campus sync done: {result}")
        except Exception as exc:
            logger.error(f"Manual campus sync failed: {exc}")

    background_tasks.add_task(_run)
    _last_sync = datetime.now(timezone.utc)

    return {
        "status":  "started",
        "message": "Campus sync running in background",
    }
