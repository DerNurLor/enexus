from datetime import datetime
from typing import Optional, List
from beanie import Document
from pymongo import IndexModel, ASCENDING, TEXT
from pydantic import Field


class Room(Document):
    room_id:   int
    name:      str
    building:  Optional[str] = None
    capacity:  Optional[int] = None  # manual seed

    subjects:      List[str] = Field(default_factory=list)
    lesson_types:  List[str] = Field(default_factory=list)
    group_ids:     List[int] = Field(default_factory=list)
    group_names:   List[str] = Field(default_factory=list)
    teacher_ids:   List[int] = Field(default_factory=list)
    teacher_names: List[str] = Field(default_factory=list)

    lessons_count: int = 0

    schedule_scraped_at: Optional[datetime] = None
    scrape_status:       str = "pending"

    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at:  datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "rooms"
        indexes = [
            IndexModel([("room_id", ASCENDING)], unique=True),
            IndexModel([("building", ASCENDING)]),
            IndexModel([("name", TEXT)], default_language="russian", name="rooms_text"),
        ]
