from fastapi import APIRouter, HTTPException
from app.models.institute import Institute

router = APIRouter(prefix="/institutes", tags=["Institutes"])


@router.get("/", summary="List all institutes")
async def list_institutes():
    institutes = await Institute.find_all().to_list()
    return institutes


@router.get("/{institute_id}", summary="Get institute by ID")
async def get_institute(institute_id: int):
    inst = await Institute.find_one(Institute.institute_id == institute_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institute not found")
    return inst
