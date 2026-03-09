from datetime import datetime
from typing import Optional, List, Dict
from beanie import Document
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from pydantic import BaseModel, Field


class Lesson(BaseModel):
    lesson_number: int
    time_start:    str
    time_end:      str
    subject:       str
    lesson_type:   Optional[str] = None
    teacher_id:    Optional[int] = None
    teacher_name:  Optional[str] = None
    room_id:       Optional[int] = None
    classroom:     Optional[str] = None
    building:      Optional[str] = None
    subgroup:      Optional[str] = None
    week_type:     Optional[str] = None
    note:          Optional[str] = None


class DaySchedule(BaseModel):
    weekday:      int
    weekday_name: str
    week_number:  int
    lessons:      List[Lesson] = []


class Group(Document):
    group_id:        int
    name:            str
    institute_id:    int
    institute_name:  str
    speciality_id:   Optional[int] = None
    speciality_name: Optional[str] = None
    course:          Optional[int] = None
    academic_year:   Optional[str] = None
    lessons_count:   int = 0
    days_count:      int = 0
    subjects:        List[str] = Field(default_factory=list)
    schedule_scraped_at: Optional[datetime] = None
    scrape_status:       str = "pending"
    scraped_at:          Optional[datetime] = None
    schedule: Dict[str, DaySchedule] = Field(default_factory=dict)

    class Settings:
        name = "groups"
        indexes = [
            IndexModel([("group_id", ASCENDING)], unique=True),
            IndexModel([("institute_id", ASCENDING)]),
            IndexModel([("course", ASCENDING)]),
            IndexModel([("schedule_scraped_at", DESCENDING)]),
            IndexModel([("scraped_at", ASCENDING)]),
            IndexModel([("name", TEXT)], default_language="russian", name="groups_text"),
        ]
