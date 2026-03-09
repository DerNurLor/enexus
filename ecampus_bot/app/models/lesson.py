from datetime import date, datetime
from typing import Optional
from beanie import Document
from pymongo import IndexModel, ASCENDING, TEXT
from pydantic import Field


class LessonDoc(Document):
    date:          date
    time_start:    str
    time_end:      str
    week_number:   int
    academic_year: str
    subject:       str
    lesson_type:   Optional[str] = None
    subgroup:      Optional[str] = None
    week_type:     Optional[str] = None
    note:          Optional[str] = None
    group_id:      int
    group_name:    str
    institute_id:   Optional[int] = None
    institute_name: Optional[str] = None
    teacher_id:    Optional[int] = None
    teacher_name:  Optional[str] = None
    room_id:       Optional[int] = None
    room_name:     Optional[str] = None
    building:      Optional[str] = None
    scraped_at:    datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "lessons"
        indexes = [
            IndexModel([("date", ASCENDING), ("group_id", ASCENDING)]),
            IndexModel([("date", ASCENDING), ("teacher_id", ASCENDING)]),
            IndexModel([("date", ASCENDING), ("room_id", ASCENDING)]),
            IndexModel([("date", ASCENDING), ("time_start", ASCENDING)]),
            IndexModel([("institute_id", ASCENDING), ("date", ASCENDING)]),
            IndexModel([("subject", ASCENDING), ("date", ASCENDING)]),
            IndexModel([("academic_year", ASCENDING), ("date", ASCENDING)]),
            IndexModel([("group_id", ASCENDING), ("week_number", ASCENDING)]),
            IndexModel([("teacher_id", ASCENDING), ("week_number", ASCENDING)]),
            IndexModel([("room_id", ASCENDING), ("week_number", ASCENDING)]),
            IndexModel(
                [("subject", TEXT), ("teacher_name", TEXT), ("room_name", TEXT), ("group_name", TEXT)],
                default_language="russian", name="lessons_text",
            ),
        ]
