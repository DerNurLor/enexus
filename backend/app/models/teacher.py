from datetime import datetime
from typing import Optional, List
from beanie import Document
from pymongo import IndexModel, ASCENDING, TEXT
from pydantic import Field


class Teacher(Document):
    teacher_id:      int
    full_name:       str
    short_name:      Optional[str] = None  # derived: Иванов И.И.
    source_url:      str = "https://ecampus.ncfu.ru"   # portal this teacher belongs to

    institute_ids:   List[int] = Field(default_factory=list)
    institute_names: List[str] = Field(default_factory=list)
    subjects:        List[str] = Field(default_factory=list)
    lesson_types:    List[str] = Field(default_factory=list)
    group_ids:       List[int] = Field(default_factory=list)
    group_names:     List[str] = Field(default_factory=list)

    lessons_count: int = 0

    schedule_scraped_at: Optional[datetime] = None
    scrape_status:       str = "pending"

    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at:  datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "teachers"
        indexes = [
            # Уникальность teacher_id + source_url: один и тот же преподаватель
            # может существовать на разных порталах — они не должны смешиваться.
            IndexModel([("teacher_id", ASCENDING), ("source_url", ASCENDING)], unique=True),
            IndexModel([("source_url", ASCENDING)]),
            IndexModel([("institute_ids", ASCENDING)]),
            IndexModel([("full_name", TEXT)], default_language="russian", name="teachers_text"),
        ]

    @staticmethod
    def derive_short_name(full_name: str) -> Optional[str]:
        """'Иванов Иван Иванович' → 'Иванов И.И.'"""
        parts = full_name.strip().split()
        if len(parts) >= 2:
            initials = ".".join(p[0] for p in parts[1:] if p) + "."
            return f"{parts[0]} {initials}"
        return None
