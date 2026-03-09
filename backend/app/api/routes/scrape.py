from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.models.scrape_log import ScrapeLog
from app.scraper.scraper import NCFUScraper

router = APIRouter(prefix="/scrape", tags=["Scraper Control"])


@router.post("/trigger", summary="Manually trigger a scrape run")
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    mode: str = "incremental",
):
    async def _run():
        scraper = NCFUScraper(triggered_by="api", mode=mode)
        await scraper.run()

    background_tasks.add_task(_run)
    return {"message": f"Scrape queued (mode={mode})"}


@router.get("/logs", summary="List recent scrape logs")
async def list_scrape_logs(limit: int = 20):
    return await ScrapeLog.find_all().sort(
        -ScrapeLog.started_at
    ).limit(limit).to_list()


@router.get("/logs/{log_id}", summary="Get a specific scrape log")
async def get_scrape_log(log_id: str):
    from beanie import PydanticObjectId
    log = await ScrapeLog.get(PydanticObjectId(log_id))
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.post("/backfill-teachers",
             summary="Extract teachers/rooms from existing DB schedules")
async def backfill_teachers(background_tasks: BackgroundTasks):
    async def _run():
        from app.models.group import Group
        from loguru import logger

        groups = await Group.find(
            {"schedule_scraped_at": {"$exists": True}}
        ).to_list()
        logger.info(f"Backfill: {len(groups)} groups")

        teachers: dict[int, dict] = {}
        rooms:    dict[int, dict] = {}
        scraper = NCFUScraper(triggered_by="backfill")

        for g in groups:
            if g.schedule:
                scraper._extract_teachers(teachers, g.schedule, g)
                scraper._extract_rooms(rooms, g.schedule, g)

        await scraper._flush_teachers(teachers)
        await scraper._flush_rooms(rooms)
        logger.info(
            f"Backfill done: {len(teachers)} teachers, {len(rooms)} rooms"
        )

    background_tasks.add_task(_run)
    return {"message": "Backfill started"}
