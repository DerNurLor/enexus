from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional
from app.models.group import Group
from app.api.routes.schedules import _needs_refresh, _do_refresh

router = APIRouter(prefix="/groups", tags=["Groups"])


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


@router.get("/", summary="List all groups (no schedule payload)")
async def list_groups(
    institute_id:  Optional[int] = Query(None),
    speciality_id: Optional[int] = Query(None),
    course:        Optional[int] = Query(None),
    q:             Optional[str] = Query(None, description="Search by group name"),
):
    filters: dict = {}
    if institute_id  is not None: filters["institute_id"]  = institute_id
    if speciality_id is not None: filters["speciality_id"] = speciality_id
    if course        is not None: filters["course"]        = course
    if q: filters["name"] = {"$regex": q, "$options": "i"}

    groups = await Group.find(filters).to_list()
    return [_group_meta(g) for g in groups]


@router.get("/{group_id}", summary="Get group with full embedded schedule")
async def get_group(group_id: int, background_tasks: BackgroundTasks):
    group = await Group.find_one(Group.group_id == group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    needs, reason = _needs_refresh(group)
    if needs:
        background_tasks.add_task(_do_refresh, group.group_id, group.name)
    return {
        **group.model_dump(),
        "refreshing": reason if needs else None,
    }


@router.get("/{group_id}/schedule", summary="Get schedule for a group")
async def get_group_schedule(group_id: int):
    group = await Group.find_one(Group.group_id == group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return {
        "group_id":            group.group_id,
        "name":                group.name,
        "speciality_name":     group.speciality_name,
        "course":              group.course,
        "academic_year":       group.academic_year,
        "schedule_scraped_at": group.schedule_scraped_at,
        "schedule":            {k: v.model_dump() for k, v in group.schedule.items()} if group.schedule else {},
    }


@router.get("/{group_id}/schedule/{date}", summary="Get schedule for a specific date (YYYY-MM-DD)")
async def get_group_day(group_id: int, date: str):
    group = await Group.find_one(Group.group_id == group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    day = group.schedule.get(date) if group.schedule else None
    if not day:
        return {"date": date, "lessons": [], "message": "No classes"}
    return {"date": date, **day.model_dump()}
