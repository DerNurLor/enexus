import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.core.config import settings
from app.scraper.scraper import NCFUScraper

_scheduler = AsyncIOScheduler(timezone=settings.cron_timezone)


def setup_scheduler() -> None:
    _scheduler.add_job(
        _run_scrape,
        IntervalTrigger(hours=settings.scrape_interval_hours),
        id="hourly_scrape",
        name="Hourly NCFU scrape",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # Cleanup old activity logs every day at settings.cleanup_hour_utc UTC
    _scheduler.add_job(
        _run_cleanup,
        CronTrigger(hour=settings.cleanup_hour_utc, minute=0, timezone="UTC"),
        id="daily_log_cleanup",
        name="Daily activity log cleanup",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    logger.info(f"Scheduler started — scrape every {settings.scrape_interval_hours}h, cleanup at {settings.cleanup_hour_utc}:00 UTC")
    loop = asyncio.get_event_loop()
    loop.call_later(5, lambda: asyncio.ensure_future(_run_scrape()))
    logger.info("First scrape in 5s.")


def shutdown_scheduler() -> None:
    _scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped.")


async def _run_scrape() -> None:
    logger.info("Scrape job triggered.")
    try:
        from app.cache.redis import get_redis
        scraper = NCFUScraper(triggered_by="scheduler")
        log = await scraper.run()
        r = get_redis()
        await r.publish("ncfu:scrape:completed", log.status)
    except Exception as exc:
        logger.error(f"Scrape job crashed: {exc}")


async def _run_cleanup() -> None:
    """Delete AuthActivityLog and AuthErrorLog documents older than settings.activity_log_ttl_days."""
    logger.info(f"Log cleanup job triggered (TTL={settings.activity_log_ttl_days}d)")
    try:
        from datetime import datetime, timedelta
        from app.auth.models import AuthActivityLog, AuthErrorLog

        cutoff = datetime.utcnow() - timedelta(days=settings.activity_log_ttl_days)

        result_a = await AuthActivityLog.find(
            AuthActivityLog.timestamp < cutoff
        ).delete()
        result_e = await AuthErrorLog.find(
            AuthErrorLog.timestamp < cutoff
        ).delete()

        deleted_a = getattr(result_a, "deleted_count", 0)
        deleted_e = getattr(result_e, "deleted_count", 0)
        logger.info(f"Log cleanup done: {deleted_a} activity, {deleted_e} error records deleted")

        from app.core.activity import log_activity
        log_activity(
            "scheduler.log_cleanup",
            details={"deleted_activity": deleted_a, "deleted_errors": deleted_e,
                     "cutoff_days": settings.activity_log_ttl_days},
        )
    except Exception as exc:
        logger.error(f"Log cleanup job crashed: {exc}")
