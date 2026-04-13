"""
backend/app/models/campus.py

Модель здания/объекта кампуса СКФУ.
Данные загружаются с https://ncfu.ru/api/campuses/list.php
и хранятся в MongoDB коллекции `campuses`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


class CampusTransport(BaseModel):
    bus:        str = ""
    trolleybus: str = ""
    tram:       str = ""


class CampusType(BaseModel):
    id:       str  # "campuses" | "hostels" | "cafe" | "banks" | "misc"
    title:    str
    en_title: str = Field("", alias="enTitle")

    model_config = {"populate_by_name": True}


class Campus(Document):
    """
    Один объект кампуса (корпус, общежитие, буфет, банкомат, etc).

    source_id    — оригинальный id из API СКФУ (строка)
    city_id      — id города из API (838=Ставрополь, 832=Пятигорск, 826=Невинномысск)
    city_title   — человекочитаемое название города
    """
    source_id:   Indexed(str, unique=False)  # type: ignore[valid-type]
    city_id:     str
    city_title:  str
    en_city_title: str = ""

    title:       str          # короткое (например "1", "6А", "Библиотека")
    full_title:  str          # полное название
    en_title:    str = ""
    en_full_title: str = ""

    address:     str
    en_address:  str = ""

    photo:       str = ""     # URL фото
    lat:         Optional[float] = None
    lon:         Optional[float] = None

    transport:   CampusTransport = Field(default_factory=CampusTransport)
    type:        CampusType

    updated_at:  datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "campuses"
        indexes = [
            IndexModel([("source_id", ASCENDING)]),
            IndexModel([("city_id",   ASCENDING)]),
            IndexModel([("type.id",   ASCENDING)]),
            IndexModel([("lat", ASCENDING), ("lon", ASCENDING)]),
            # Составной — быстрый запрос «все корпуса города»
            IndexModel([("city_id", ASCENDING), ("type.id", ASCENDING)]),
        ]
