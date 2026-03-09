from datetime import datetime
from typing import Optional
from beanie import Document
from pymongo import IndexModel, ASCENDING, TEXT


class Institute(Document):
    institute_id: int
    short_name:   str
    name:         str
    branch_id:    int
    is_synthetic: bool = False
    scraped_at:   Optional[datetime] = None

    class Settings:
        name = "institutes"
        indexes = [
            IndexModel([("institute_id", ASCENDING)], unique=True),
            IndexModel([("scraped_at", ASCENDING)]),
            IndexModel([("name", TEXT), ("short_name", TEXT)],
                       default_language="russian", name="institutes_text"),
        ]
