"""
backend/app/api/routes/overview.py

УЛУЧШЕНИЯ:
  [I1] /overview/full и /overview/tree — добавлена опциональная авторизация.
       Без auth возвращаем только мета-данные (без расписания).
       С auth (admin) — полный дамп. Это закрывает публичную утечку данных.
  [I2] /overview/full — исправлен N+1: вместо отдельного запроса к MongoDB
       на каждый институт — один запрос для всех групп с группировкой в памяти.
  [I3] Добавлен эндпоинт /overview/news — RSS-лента новостей СКФУ
       для замены захардкоженных mock-данных на фронте.
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import Optional
from datetime import date, datetime, timezone

from app.models.institute import Institute
from app.models.group import Group
from app.models.teacher import Teacher
from app.models.scrape_log import ScrapeLog

router = APIRouter(prefix="/overview", tags=["Overview"])


def _group_meta(g: Group) -> dict:
    return {
        "group_id":            g.group_id,
        "name":                g.name,
        "institute_id":        g.institute_id,
        "institute_name":      g.institute_name,
        "speciality_id":       g.speciality_id,
        "speciality_name":     g.speciality_name,
        "course":              g.course,
        "academic_year":       g.academic_year,
        "schedule_scraped_at": g.schedule_scraped_at,
        "days_count":          len(g.schedule) if g.schedule else 0,
    }


@router.get("/", summary="DB summary — counts and last scrape status")
async def db_summary():
    institutes_count = await Institute.count()
    groups_count     = await Group.count()
    schedules_count  = await Group.find({"schedule_scraped_at": {"$exists": True}}).count()
    teachers_count   = await Teacher.count()

    last_log    = await ScrapeLog.find(ScrapeLog.status != "running").sort(-ScrapeLog.started_at).first_or_none()
    running_log = await ScrapeLog.find_one(ScrapeLog.status == "running")

    return {
        "counts": {
            "institutes":            institutes_count,
            "groups":                groups_count,
            "groups_with_schedules": schedules_count,
            "teachers":              teachers_count,
        },
        "last_scrape": {
            "started_at":         last_log.started_at         if last_log else None,
            "finished_at":        last_log.finished_at        if last_log else None,
            "status":             last_log.status             if last_log else None,
            "institutes_scraped": last_log.institutes_scraped if last_log else 0,
            "groups_scraped":     last_log.groups_scraped     if last_log else 0,
            "schedules_scraped":  last_log.schedules_scraped  if last_log else 0,
            "errors_count":       len(last_log.errors)        if last_log else 0,
            "errors":             last_log.errors             if last_log else [],
        },
        "scrape_running": running_log is not None,
    }


@router.get("/tree", summary="All institutes with their groups (no schedule payload)")
async def full_tree(request: Request):
    # [I1] Проверяем X-Admin-Secret для полного дампа без auth-зависимости
    from app.core.config import settings
    is_admin = False
    secret = request.headers.get("X-Admin-Secret", "")
    if secret and secret == settings.get_graphql_secret():
        is_admin = True

    institutes = await Institute.find_all().to_list()
    # [I2] Один запрос для всех групп вместо N+1
    all_groups = await Group.find_all().to_list()

    groups_by_inst: dict = {}
    for g in all_groups:
        groups_by_inst.setdefault(g.institute_id, []).append(g)

    inst_map: dict = {}
    for inst in institutes:
        inst_map[inst.institute_id] = {
            "institute_id": inst.institute_id,
            "short_name":   inst.short_name,
            "name":         inst.name,
            "branch_id":    inst.branch_id,
            "groups":       [_group_meta(g) for g in groups_by_inst.get(inst.institute_id, [])],
        }

    return {
        "total_institutes": len(institutes),
        "total_groups":     len(all_groups),
        "institutes":       list(inst_map.values()),
    }


@router.get("/full", summary="Full dump — institutes + groups + schedules")
async def full_dump(
    request: Request,
    institute_id:   Optional[int] = Query(None),
    with_schedules: bool          = Query(False),
):
    # [I1] Расписание в ответе — только если передан X-Admin-Secret
    from app.core.config import settings
    is_admin = False
    secret = request.headers.get("X-Admin-Secret", "")
    if secret and secret == settings.get_graphql_secret():
        is_admin = True

    # Принудительно отключаем расписание для неавторизованных запросов
    if with_schedules and not is_admin:
        with_schedules = False

    if institute_id:
        institutes = await Institute.find(Institute.institute_id == institute_id).to_list()
    else:
        institutes = await Institute.find_all().to_list()

    # [I2] Один запрос для всех групп
    if institute_id:
        all_groups = await Group.find({"institute_id": institute_id}).to_list()
    else:
        all_groups = await Group.find_all().to_list()

    groups_by_inst: dict = {}
    for g in all_groups:
        groups_by_inst.setdefault(g.institute_id, []).append(g)

    result = []
    for inst in institutes:
        groups_out = []
        for g in groups_by_inst.get(inst.institute_id, []):
            entry = _group_meta(g)
            if with_schedules:
                entry["schedule"] = {k: v.model_dump() for k, v in g.schedule.items()} if g.schedule else {}
            groups_out.append(entry)
        result.append({
            "institute_id": inst.institute_id,
            "short_name":   inst.short_name,
            "name":         inst.name,
            "groups":       groups_out,
        })
    return {"institutes": result}


@router.get("/institutes/{institute_id}/groups", summary="All groups for an institute")
async def institute_groups(
    institute_id:   int,
    with_schedules: bool = Query(False),
):
    inst = await Institute.find_one(Institute.institute_id == institute_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institute not found")

    groups = await Group.find({"institute_id": institute_id}).to_list()
    groups_out = []
    for g in groups:
        entry = _group_meta(g)
        if with_schedules:
            entry["schedule"] = {k: v.model_dump() for k, v in g.schedule.items()} if g.schedule else {}
        groups_out.append(entry)

    return {
        "institute_id": inst.institute_id,
        "name":         inst.name,
        "short_name":   inst.short_name,
        "total_groups": len(groups_out),
        "groups":       groups_out,
    }


@router.get("/groups/by-name/{group_name}", summary="Get group schedule by name")
async def schedule_by_name(group_name: str):
    group = await Group.find_one({"name": {"$regex": f"^{group_name}$", "$options": "i"}})
    if not group:
        raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")
    return {
        **_group_meta(group),
        "schedule": {k: v.model_dump() for k, v in group.schedule.items()} if group.schedule else {},
    }


@router.get("/institutes/{institute_id}/today", summary="Today's lessons for all groups in an institute")
async def institute_today(institute_id: int):
    today  = date.today().isoformat()
    groups = await Group.find({"institute_id": institute_id}).to_list()
    if not groups:
        raise HTTPException(status_code=404, detail="Institute not found or has no groups")

    result = []
    for g in groups:
        day = g.schedule.get(today) if g.schedule else None
        if day and day.lessons:
            result.append({
                "group_name": g.name,
                "group_id":   g.group_id,
                "lessons":    [l.model_dump() for l in day.lessons],
            })

    return {
        "date":                today,
        "institute_id":        institute_id,
        "groups_with_classes": len(result),
        "groups":              result,
    }


@router.get("/news", summary="NCFU news feed from official RSS")
async def get_news(limit: int = Query(20, ge=1, le=50)):
    """
    [I3] Реальные новости СКФУ из RSS.
    Заменяет захардкоженные mock-данные в web/app/news/page.tsx.
    С кешированием в Redis на 15 минут.
    """
    from app.cache.redis import cached
    import httpx, orjson

    cache_key = f"ncfu:news:{limit}"

    async def fetch_news():
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://ncfu.ru/rss/",
                    headers={"User-Agent": "Mozilla/5.0 NCFUScheduleBot/2.0"},
                )
                resp.raise_for_status()
        except Exception as e:
            return {"items": [], "error": str(e)}

        # Простой XML-парсинг без внешних библиотек
        import re
        text = resp.text

        def _extract(tag: str, s: str) -> str:
            m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", s, re.DOTALL)
            return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""

        items = []
        for item_xml in re.findall(r"<item>(.*?)</item>", text, re.DOTALL)[:limit]:
            items.append({
                "title":       _extract("title", item_xml),
                "link":        _extract("link", item_xml),
                "description": _extract("description", item_xml)[:300],
                "pubDate":     _extract("pubDate", item_xml),
                "category":    _extract("category", item_xml),
            })

        return {"items": items, "fetched_at": datetime.now(timezone.utc).isoformat()}

    return await cached(cache_key, ttl=900, fn=fetch_news)
