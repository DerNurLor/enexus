"""
Avatar downloading service.
On Telegram login, fetches the user's profile photo and saves it locally.
"""
from __future__ import annotations

import os
import hashlib
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from app.core.config import settings

AVATAR_DIR = Path("/app/static/avatars")


async def fetch_and_save_avatar(tg_id: int, bot_token: str) -> Optional[str]:
    """
    Download the user's Telegram profile photo.

    Returns the local path (relative to /app/static) on success, None on failure.
    The file is saved as /app/static/avatars/{tg_id}.jpg
    """
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    local_path = AVATAR_DIR / f"{tg_id}.jpg"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Step 1: get user profile photos
            photos_resp = await client.get(
                f"https://api.telegram.org/bot{bot_token}/getUserProfilePhotos",
                params={"user_id": tg_id, "limit": 1},
            )
            photos_resp.raise_for_status()
            photos_data = photos_resp.json()

            if not photos_data.get("ok") or not photos_data["result"]["total_count"]:
                logger.debug(f"No profile photo for tg_id={tg_id}")
                return None

            # Get the largest size of the first photo
            photos = photos_data["result"]["photos"][0]
            file_id = max(photos, key=lambda p: p["file_size"])["file_id"]

            # Step 2: get file path on Telegram servers
            file_resp = await client.get(
                f"https://api.telegram.org/bot{bot_token}/getFile",
                params={"file_id": file_id},
            )
            file_resp.raise_for_status()
            file_data = file_resp.json()

            if not file_data.get("ok"):
                return None

            file_path = file_data["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

            # Step 3: download and save
            img_resp = await client.get(download_url)
            img_resp.raise_for_status()

            local_path.write_bytes(img_resp.content)
            logger.info(f"Avatar saved for tg_id={tg_id} → {local_path}")
            return f"avatars/{tg_id}.jpg"

    except httpx.HTTPError as exc:
        logger.warning(f"Avatar download HTTP error for tg_id={tg_id}: {exc}")
        return None
    except Exception as exc:
        logger.warning(f"Avatar download failed for tg_id={tg_id}: {exc}")
        return None


def get_avatar_url(tg_id: int) -> Optional[str]:
    """Return the public URL for the locally saved avatar, if it exists."""
    local = AVATAR_DIR / f"{tg_id}.jpg"
    if local.exists():
        base = settings.webhook_base_url.rstrip("/")
        return f"{base}/static/avatars/{tg_id}.jpg"
    return None
