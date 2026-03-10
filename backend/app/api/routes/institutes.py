from fastapi import APIRouter, HTTPException
from app.models.institute import Institute

router = APIRouter(prefix="/institutes", tags=["Institutes"])


@router.get("/", summary="List all institutes")
async def list_institutes():
    institutes = await Institute.find_all().to_list()
    return institutes


@router.get("/with-buildings", summary="Institutes with their associated buildings")
async def institutes_with_buildings():
    """Returns each institute with the buildings where its groups have classes."""
    from app.models.room import Room
    from app.models.group import Group

    try:
        all_rooms = await Room.find_all().to_list()
        all_buildings = sorted({r.building for r in all_rooms if r.building})

        institutes = await Institute.find_all().sort("short_name").to_list()

        result = []
        for inst in institutes:
            groups = await Group.find({"institute_id": inst.institute_id}).to_list()
            group_ids = {g.group_id for g in groups}
            if not group_ids:
                result.append({"institute_id": inst.institute_id, "short_name": inst.short_name,
                                "name": inst.name, "buildings": []})
                continue
            rooms_for_inst = await Room.find(
                {"group_ids": {"$in": list(group_ids)}, "building": {"$ne": None}}
            ).to_list()
            buildings_for_inst = sorted({r.building for r in rooms_for_inst if r.building})
            result.append({"institute_id": inst.institute_id, "short_name": inst.short_name,
                           "name": inst.name, "buildings": buildings_for_inst})

        result.sort(key=lambda x: (len(x["buildings"]) == 0, x["short_name"]))
        return {"institutes": result, "all_buildings": all_buildings}
    except Exception as exc:
        return {"institutes": [], "all_buildings": []}


@router.get("/{institute_id}", summary="Get institute by ID")
async def get_institute(institute_id: int):
    inst = await Institute.find_one(Institute.institute_id == institute_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institute not found")
    return inst

