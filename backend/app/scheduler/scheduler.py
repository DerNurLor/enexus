"""
backend/app/scheduler/scheduler.py

ИСПРАВЛЕНИЯ:
  [F1] asyncio.get_event_loop() deprecated в Python 3.10+ и выбрасывает DeprecationWarning,
       а в Python 3.12 в не-async контексте выбрасывает RuntimeError.
       Заменено на asyncio.get_running_loop() + loop.call_later().
  [F2] datetime.utcnow() в _run_cleanup() заменён на datetime.now(timezone.utc) —
       utcnow() deprecated и создаёт naive datetime, что ломает сравнение с Beanie-документами
       у которых timezone-aware timestamps (после исправления models.py).
  [F3] import asyncio внутри start_ecampus_worker() был избыточным (уже импортирован вверху).
"""
import asyncio
from datetime import datetime, timezone, timedelta

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

    _scheduler.add_job(
        _run_cleanup,
        CronTrigger(hour=settings.cleanup_hour_utc, minute=0, timezone="UTC"),
        id="daily_log_cleanup",
        name="Daily activity log cleanup",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.add_job(
        _run_ecampus_sync,
        CronTrigger(hour=3, minute=0, timezone="UTC"),
        id="daily_ecampus_sync",
        name="Daily eCampus sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.add_job(
        _retry_failed_ecampus_syncs,
        IntervalTrigger(hours=2),
        id="retry_failed_ecampus_syncs",
        name="Retry failed eCampus syncs (backoff)",
        replace_existing=True,
        misfire_grace_time=600,
    )

    _scheduler.add_job(
        _run_campus_sync,
        CronTrigger(hour=4, minute=30, timezone="UTC"),
        id="daily_campus_sync",
        name="Daily campus data sync from NCFU API",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    logger.info(
        f"Scheduler started — scrape every {settings.scrape_interval_hours}h, "
        f"cleanup at {settings.cleanup_hour_utc}:00 UTC"
    )

    # [F1] Используем get_running_loop() — мы находимся внутри async lifespan,
    #      поэтому event loop уже запущен и get_running_loop() безопасен.
    loop = asyncio.get_running_loop()
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
    """Delete AuthActivityLog and AuthErrorLog documents older than activity_log_ttl_days."""
    logger.info(f"Log cleanup job triggered (TTL={settings.activity_log_ttl_days}d)")
    try:
        from app.auth.models import AuthActivityLog, AuthErrorLog

        # [F2] timezone-aware datetime вместо deprecated naive utcnow()
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.activity_log_ttl_days)

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
            details={
                "deleted_activity": deleted_a,
                "deleted_errors": deleted_e,
                "cutoff_days": settings.activity_log_ttl_days,
            },
        )
    except Exception as exc:
        logger.error(f"Log cleanup job crashed: {exc}")


async def _run_ecampus_sync() -> None:
    """Ежедневная синхронизация всех пользователей eCampus."""
    try:
        from app.ecampus.sync_service import sync_all_users
        result = await sync_all_users()
        logger.info(f"eCampus daily sync enqueued: {result}")
    except Exception as exc:
        logger.error(f"eCampus daily sync error: {exc}")


async def start_ecampus_worker() -> None:
    """Запускает воркер очереди задач eCampus."""
    # [F3] Убран лишний import asyncio внутри функции — уже импортирован вверху
    from app.ecampus.queue import get_queue
    from app.ecampus.sync_service import task_handler
    logger.info("Starting eCampus queue worker...")
    asyncio.create_task(get_queue().start_worker(task_handler))


async def _retry_failed_ecampus_syncs() -> None:
    """Каждые 2 часа перезапускает упавшие синхронизации с exponential backoff."""
    try:
        from app.ecampus.sync_service import retry_failed_syncs
        result = await retry_failed_syncs()
        if result["enqueued"]:
            logger.info(f"eCampus retry: enqueued={result['enqueued']} skipped={result['skipped']}")
    except Exception as exc:
        logger.error(f"eCampus retry job crashed: {exc}")


async def _run_campus_sync() -> None:
    """Ежедневная синхронизация данных кампусов из API СКФУ."""
    try:
        from app.scraper.campus_scraper import sync_campuses
        result = await sync_campuses()
        logger.info(f"Campus daily sync done: {result}")
    except Exception as exc:
        logger.error(f"Campus daily sync error: {exc}")
