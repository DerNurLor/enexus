from datetime import datetime, date
from typing import Optional, List
from beanie import Document
from pymongo import IndexModel, ASCENDING, DESCENDING
from pydantic import BaseModel, Field


class Lesson(BaseModel):
    lesson_number: int
    time_start: str
    time_end: str
    subject: str
    lesson_type: Optional[str] = None
    teacher_name: Optional[str] = None
    classroom: Optional[str] = None
    building: Optional[str] = None
    subgroup: Optional[int] = None
    week_type: Optional[str] = None
    note: Optional[str] = None


class DaySchedule(BaseModel):
    date: date
    weekday: int
    weekday_name: str
    week_number: int
    lessons: List[Lesson] = []


class Schedule(Document):
    group_id: int
    group_name: str
    institute_id: Optional[int] = None
    academic_year: str
    semester: Optional[int] = None
    days: List[DaySchedule] = []
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    scrape_duration_sec: Optional[float] = None

    class Settings:
        name = "schedules"
        indexes = [
            IndexModel([("group_id", ASCENDING), ("academic_year", ASCENDING)], unique=True),
            IndexModel([("scraped_at", DESCENDING)]),
        ]
