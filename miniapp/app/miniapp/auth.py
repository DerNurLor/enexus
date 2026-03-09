"""
Telegram Mini App initData validation (HMAC-SHA256).

Official algorithm:
  1. Parse initData query string
  2. Remove the 'hash' field, collect remaining key=value pairs
  3. Sort them alphabetically, join with '\n'
  4. HMAC-SHA256 with key = HMAC-SHA256("WebAppData", bot_token)
  5. Compare with the received hash (constant-time)

Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.parse import parse_qsl, unquote

from fastapi import HTTPException, status
from loguru import logger

from app.core.config import settings


MAX_AGE_SECONDS = 86_400   # 24 h — Telegram recommends re-auth after this


def validate_init_data(init_data: str, max_age: int = MAX_AGE_SECONDS) -> dict:
    """
    Validate Telegram WebApp initData and return the parsed payload.
    Raises HTTP 401 on any failure.
    """
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid initData format")

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing hash in initData")

    # Build the data-check string
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))

    # Derive secret key
    secret_key = hmac.new(
        b"WebAppData",
        settings.telegram_bot_token.encode(),
        hashlib.sha256,
    ).digest()

    expected = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        logger.warning("initData hash mismatch")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "initData signature invalid")

    # Check freshness
    auth_date = int(pairs.get("auth_date", "0"))
    if max_age and (time.time() - auth_date) > max_age:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "initData expired")

    # Parse nested user JSON
    result = dict(pairs)
    if "user" in result:
        try:
            result["user"] = json.loads(unquote(result["user"]))
        except Exception:
            pass

    return result
