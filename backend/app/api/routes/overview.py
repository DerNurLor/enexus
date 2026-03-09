from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date

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
async def full_tree():
    institutes = await Institute.find_all().to_list()
    groups     = await Group.find_all().to_list()

    inst_map: dict = {}
    for inst in institutes:
        inst_map[inst.institute_id] = {
            "institute_id": inst.institute_id,
            "short_name":   inst.short_name,
            "name":         inst.name,
            "branch_id":    inst.branch_id,
            "groups":       [],
        }
    for g in groups:
        if g.institute_id in inst_map:
            inst_map[g.institute_id]["groups"].append(_group_meta(g))

    return {
        "total_institutes": len(institutes),
        "total_groups":     len(groups),
        "institutes":       list(inst_map.values()),
    }


@router.get("/full", summary="Full dump — institutes + groups + schedules")
async def full_dump(
    institute_id:   Optional[int] = Query(None),
    with_schedules: bool          = Query(True),
):
    if institute_id:
        institutes = await Institute.find(Institute.institute_id == institute_id).to_list()
    else:
        institutes = await Institute.find_all().to_list()

    result = []
    for inst in institutes:
        groups = await Group.find({"institute_id": inst.institute_id}).to_list()
        groups_out = []
        for g in groups:
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
