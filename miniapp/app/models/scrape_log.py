from datetime import datetime
from typing import Optional
from beanie import Document
from pymongo import IndexModel, ASCENDING, DESCENDING
from pydantic import Field


class ScrapeLog(Document):
    started_at:        datetime = Field(default_factory=datetime.utcnow)
    finished_at:       Optional[datetime] = None
    status:            str = "running"
    mode:              str = "incremental"
    groups_total:      int = 0
    groups_scraped:    int = 0
    groups_skipped:    int = 0
    groups_failed:     int = 0
    lessons_written:   int = 0
    lessons_unchanged: int = 0
    teachers_upserted: int = 0
    rooms_upserted:    int = 0
    errors:            list[str] = Field(default_factory=list)
    triggered_by:      str = "scheduler"

    class Settings:
        name = "scrape_logs"
        indexes = [
            IndexModel([("started_at", DESCENDING)]),
            IndexModel([("status", ASCENDING)]),
        ]
