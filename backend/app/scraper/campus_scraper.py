"""
backend/app/scraper/campus_scraper.py

Загрузчик данных кампусов СКФУ из публичного API.

Эндпоинт: https://ncfu.ru/api/campuses/list.php
Права доступа: публичный (Access-Control-Allow-Origin: *)

Алгоритм:
  1. GET https://ncfu.ru/api/campuses/list.php
  2. Итерируем по городам → объектам
  3. Upsert в MongoDB по source_id (не дублируем при повторном запуске)
  4. Возвращаем статистику: created / updated / skipped

Запускается:
  - При старте приложения (startup event, если коллекция пуста)
  - Планировщиком раз в 24 часа (данные меняются редко)
  - Вручную через POST /campuses/sync (admin)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from app.models.campus import Campus, CampusTransport, CampusType

CAMPUSES_API_URL = "https://ncfu.ru/api/campuses/list.php"
REQUEST_TIMEOUT  = 20   # секунд
REQUEST_HEADERS  = {
    "User-Agent": "Mozilla/5.0 NCFUScheduleBot/2.0",
    "Accept":     "application/json",
}


def _parse_float(value: Any) -> float | None:
    """Безопасно парсит float из строки (в API бывают пробелы)."""
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return None


def _parse_item(item: dict, city_id: str, city_title: str, en_city_title: str) -> Campus | None:
    """Преобразует один объект из JSON-ответа API в Beanie-документ."""
    source_id = str(item.get("id", "")).strip()
    if not source_id:
        return None

    transport_raw = item.get("transport") or {}
    transport = CampusTransport(
        bus=transport_raw.get("bus", "") or "",
        trolleybus=transport_raw.get("trolleybus", "") or "",
        tram=transport_raw.get("tram", "") or "",
    )

    type_raw = item.get("type") or {}
    campus_type = CampusType(
        id=type_raw.get("id", "misc"),
        title=type_raw.get("title", "Дополнительно"),
        enTitle=type_raw.get("enTitle", ""),
    )

    return Campus(
        source_id=source_id,
        city_id=city_id,
        city_title=city_title,
        en_city_title=en_city_title,
        title=(item.get("title") or "").strip(),
        full_title=(item.get("fullTitle") or item.get("title") or "").strip(),
        en_title=(item.get("enTitle") or "").strip(),
        en_full_title=(item.get("enFullTitle") or "").strip(),
        address=(item.get("address") or "").strip(),
        en_address=(item.get("enAddress") or "").strip(),
        photo=(item.get("photo") or "").strip(),
        lat=_parse_float(item.get("lat")),
        lon=_parse_float(item.get("lon")),
        transport=transport,
        type=campus_type,
        updated_at=datetime.now(timezone.utc),
    )


async def fetch_campuses_from_api() -> list[dict]:
    """Делает HTTP-запрос к API СКФУ и возвращает сырой JSON."""
    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        headers=REQUEST_HEADERS,
        follow_redirects=True,
    ) as client:
        resp = await client.get(CAMPUSES_API_URL)
        resp.raise_for_status()
        return resp.json()


async def sync_campuses() -> dict:
    """
    Полная синхронизация: загружает данные из API и делает upsert в MongoDB.

    Возвращает:
        {
          "created": int,   — новых записей
          "updated": int,   — обновлённых
          "skipped": int,   — без изменений (photo/address совпадают)
          "errors":  int,   — объектов с ошибкой парсинга
          "total":   int,   — всего объектов в API
        }
    """
    logger.info("CampusScraper: starting sync from NCFU API...")

    try:
        raw_data = await fetch_campuses_from_api()
    except httpx.HTTPError as exc:
        logger.error(f"CampusScraper: HTTP error — {exc}")
        raise
    except Exception as exc:
        logger.error(f"CampusScraper: unexpected error fetching API — {exc}")
        raise

    created = updated = skipped = errors = 0
    total   = 0

    for city in raw_data:
        city_id        = str(city.get("id", ""))
        city_title     = city.get("title", "")
        en_city_title  = city.get("enTitle", "")

        for item in city.get("items", []):
            total += 1
            try:
                doc = _parse_item(item, city_id, city_title, en_city_title)
                if doc is None:
                    errors += 1
                    continue

                # Upsert по source_id
                existing = await Campus.find_one(Campus.source_id == doc.source_id)

                if existing is None:
                    await doc.insert()
                    created += 1
                else:
                    # Обновляем только если что-то изменилось (адрес, фото, координаты)
                    changed = (
                        existing.full_title  != doc.full_title  or
                        existing.address     != doc.address     or
                        existing.photo       != doc.photo       or
                        existing.lat         != doc.lat         or
                        existing.lon         != doc.lon         or
                        existing.transport   != doc.transport
                    )
                    if changed:
                        await existing.set({
                            "full_title":    doc.full_title,
                            "en_full_title": doc.en_full_title,
                            "address":       doc.address,
                            "en_address":    doc.en_address,
                            "photo":         doc.photo,
                            "lat":           doc.lat,
                            "lon":           doc.lon,
                            "transport":     doc.transport.model_dump(),
                            "type":          doc.type.model_dump(by_alias=True),
                            "updated_at":    datetime.now(timezone.utc),
                        })
                        updated += 1
                    else:
                        skipped += 1

            except Exception as exc:
                logger.warning(f"CampusScraper: error processing item {item.get('id')}: {exc}")
                errors += 1

    result = {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors":  errors,
        "total":   total,
    }
    logger.info(f"CampusScraper: sync done — {result}")
    return result


async def ensure_campuses_loaded() -> None:
    """
    Вызывается при старте приложения.
    Если коллекция пуста — запускает полную синхронизацию.
    Если есть данные — пропускает (синхронизация будет по расписанию).
    """
    count = await Campus.count()
    if count == 0:
        logger.info("CampusScraper: collection is empty — running initial sync...")
        try:
            result = await sync_campuses()
            logger.info(f"CampusScraper: initial sync complete: {result}")
        except Exception as exc:
            logger.error(f"CampusScraper: initial sync failed: {exc}")
    else:
        logger.info(f"CampusScraper: {count} campuses already in DB — skip initial sync.")
