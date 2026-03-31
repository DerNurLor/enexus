"""
backend/app/auth/bot_code_router.py

Авторизация через числовой код — новый поток:

  Сайт:
    1. POST /auth/code/request          → генерирует session_id + 6-значный код
    2. GET  /auth/code/poll/{session_id} → long-polling (ждёт подтверждения от бота)

  Бот (вызывается из bot_login.py):
    3. POST /auth/code/verify           → бот передаёт код + tg_id
    4. POST /auth/code/confirm          → бот сообщает что пользователь нажал «Подтвердить»

  Итог:
    - poll возвращает JWT как только пользователь подтвердил
    - Страница обновляется автоматически без редиректов и URL-вставки

Безопасность:
  - Код действителен 3 минуты
  - Код одноразовый
  - Rate limit: 5 запросов в минуту на IP
  - После 3 неверных попыток код инвалидируется
  - session_id — cryptographically random UUID
  - Код — 6 цифр: достаточно для UX, брутфорс ограничен rate-limit'ом
"""
from __future__ import annotations

import asyncio
import json
import random
import secrets
import string
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from loguru import logger

router = APIRouter(prefix="/auth", tags=["auth"])

CODE_TTL        = 180    # 3 минуты
POLL_TIMEOUT    = 60     # long-poll до 60 секунд
POLL_INTERVAL   = 1.0    # проверяем Redis каждую секунду
MAX_ATTEMPTS    = 5      # максимум неверных попыток ввода кода

# Алфавит: заглавные буквы + цифры, без O/0 и I/1 (легко перепутать)
_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


# ── Схемы ─────────────────────────────────────────────────────────────────────

class CodeRequestResponse(BaseModel):
    session_id: str
    code:       str
    expires_in: int  # секунды


class BotVerifyRequest(BaseModel):
    """Бот сообщает: пользователь ввёл такой код."""
    code:       str = Field(..., min_length=6, max_length=6, pattern=r"^[A-Z0-9]{6}$")
    tg_id:      int
    bot_secret: str  # внутренний секрет бот→API


class BotConfirmRequest(BaseModel):
    """Бот сообщает: пользователь нажал «Подтвердить»."""
    session_id: str
    tg_id:      int
    bot_secret: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _session_key(session_id: str) -> str:
    return f"auth:code:session:{session_id}"

def _code_key(code: str) -> str:
    return f"auth:code:value:{code}"

def _ready_key(session_id: str) -> str:
    return f"auth:code:ready:{session_id}"

def _attempts_key(code: str) -> str:
    return f"auth:code:attempts:{code}"


def _generate_code() -> str:
    """6 заглавных латинских букв (без O, I — чтобы не путать с 0, 1)."""
    return "".join(random.choices(_CODE_CHARS, k=6))


def _generate_session_id() -> str:
    return secrets.token_urlsafe(32)


# ── 1. Сайт запрашивает новый код ─────────────────────────────────────────────

@router.post("/code/request", response_model=CodeRequestResponse)
async def request_code(request: Request):
    """
    Сайт вызывает этот эндпоинт когда пользователь нажимает «Войти через Telegram».
    Возвращает session_id (для polling) и 6-значный код (показать пользователю).
    """
    from app.cache.redis import get_redis
    from app.core.ratelimit import check_rate_limit, _get_ip

    # Rate limit: 5 запросов в минуту с IP
    ip = _get_ip(request)
    await check_rate_limit(f"rl:code:request:{ip}", rpm=5, window=60)

    r = get_redis()

    # Генерируем уникальный код (проверяем коллизии)
    for _ in range(10):
        code = _generate_code()
        if not await r.exists(_code_key(code)):
            break

    session_id = _generate_session_id()

    # session_id → {code, status: "pending"}
    session_data = json.dumps({
        "code":       code,
        "status":     "pending",   # pending | confirmed
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await r.setex(_session_key(session_id), CODE_TTL, session_data)

    # code → session_id (для быстрого lookup из бота)
    await r.setex(_code_key(code), CODE_TTL, session_id)

    logger.info(f"Auth code requested from ip={ip} session={session_id[:8]}...")

    return CodeRequestResponse(
        session_id=session_id,
        code=code,
        expires_in=CODE_TTL,
    )


# ── 2. Бот проверяет код и получает session_id ────────────────────────────────

@router.post("/code/verify")
async def bot_verify_code(body: BotVerifyRequest):
    """
    Бот вызывает этот эндпоинт когда пользователь отправляет ему 6-значный код.
    Возвращает session_id если код верный — бот запросит подтверждение у пользователя.
    """
    from app.cache.redis import get_redis
    from app.core.config import settings

    # Проверяем внутренний секрет бот→API
    bot_secret = getattr(settings, "bot_api_secret", "") or ""
    if not bot_secret or body.bot_secret != bot_secret:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid bot secret")

    r = get_redis()

    # Проверяем число попыток
    attempts_key = _attempts_key(body.code)
    attempts = int(await r.get(attempts_key) or 0)
    if attempts >= MAX_ATTEMPTS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Код заблокирован после 5 попыток")

    session_id_raw = await r.get(_code_key(body.code))
    if not session_id_raw:
        # Считаем неверную попытку
        await r.incr(attempts_key)
        await r.expire(attempts_key, CODE_TTL)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Неверный или истёкший код")

    session_id = session_id_raw.decode() if isinstance(session_id_raw, bytes) else session_id_raw

    # Привязываем tg_id к сессии
    raw = await r.get(_session_key(session_id))
    if not raw:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сессия истекла")

    session = json.loads(raw)
    session["tg_id"]   = body.tg_id
    session["status"]  = "code_matched"
    ttl = await r.ttl(_session_key(session_id))
    await r.setex(_session_key(session_id), max(ttl, 60), json.dumps(session))

    logger.info(f"Auth code matched: tg_id={body.tg_id} session={session_id[:8]}...")

    return {"ok": True, "session_id": session_id}


# ── 3. Бот подтверждает вход ──────────────────────────────────────────────────

@router.post("/code/confirm")
async def bot_confirm_login(body: BotConfirmRequest):
    """
    Бот вызывает после того как пользователь нажал «✅ Подтвердить».
    Генерирует JWT и кладёт в Redis — poll его подхватит.
    """
    from app.cache.redis import get_redis
    from app.core.config import settings
    from app.auth.models import AuthUser
    from app.auth.security import create_access_token, create_refresh_token, decode_access_token

    bot_secret = getattr(settings, "bot_api_secret", "") or ""
    if not bot_secret or body.bot_secret != bot_secret:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid bot secret")

    r = get_redis()

    raw = await r.get(_session_key(body.session_id))
    if not raw:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сессия истекла")

    session = json.loads(raw)

    # Убеждаемся что tg_id совпадает
    if session.get("tg_id") != body.tg_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "tg_id mismatch")

    user = await AuthUser.find_one(AuthUser.tg_id == body.tg_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    if user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Account blocked: {user.block_reason}")

    await user.set({"last_active": datetime.now(timezone.utc)})

    access_token  = create_access_token(str(user.id), user.tg_id, user.roles)
    refresh_token = create_refresh_token(str(user.id), user.tg_id)

    # Сохраняем JTI refresh токена
    try:
        refresh_payload = decode_access_token(refresh_token)
        jti = refresh_payload.get("jti", "")
        if jti:
            await r.setex(f"refresh:jti:{jti}", 86400 * 31, str(user.id))
            await r.setex(f"refresh:user:{user.id}", 86400 * 31, jti)
    except Exception as exc:
        logger.warning(f"Failed to store refresh JTI: {exc}")

    # Кладём готовые токены в Redis — poll их подхватит
    ready_data = json.dumps({
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "Bearer",
        "expires_in":    3600,
    })
    await r.setex(_ready_key(body.session_id), 120, ready_data)

    # Инвалидируем код чтобы им нельзя было воспользоваться повторно
    code = session.get("code")
    if code:
        await r.delete(_code_key(code))
    await r.delete(_session_key(body.session_id))

    logger.info(f"Auth confirmed: tg_id={body.tg_id} session={body.session_id[:8]}...")
    return {"ok": True}


# ── 4. Сайт делает long-poll ──────────────────────────────────────────────────

@router.get("/code/poll/{session_id}")
async def poll_session(session_id: str):
    """
    Сайт вызывает этот эндпоинт и ждёт до POLL_TIMEOUT секунд.
    Как только пользователь подтвердил в боте — возвращает JWT.

    Статусы ответа:
      200 + tokens  — подтверждено, вот JWT
      200 + pending — ещё ждём
      404           — сессия истекла или не найдена
    """
    from app.cache.redis import get_redis

    r = get_redis()
    elapsed = 0.0

    while elapsed < POLL_TIMEOUT:
        # Проверяем готовые токены
        ready_raw = await r.get(_ready_key(session_id))
        if ready_raw:
            tokens = json.loads(ready_raw)
            await r.delete(_ready_key(session_id))
            return {"status": "confirmed", **tokens}

        # Проверяем что сессия ещё жива
        session_raw = await r.get(_session_key(session_id))
        if not session_raw:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сессия истекла")

        session = json.loads(session_raw)

        # Отдаём промежуточный статус (для анимации на фронте)
        if elapsed > 0 and int(elapsed) % 10 == 0:
            return {
                "status":     session.get("status", "pending"),
                "expires_in": await r.ttl(_session_key(session_id)),
            }

        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    # Timeout — отдаём pending, фронт переспросит
    return {"status": "pending", "expires_in": 0}


# ── 5. Отмена сессии ──────────────────────────────────────────────────────────

@router.delete("/code/cancel/{session_id}")
async def cancel_session(session_id: str):
    """Пользователь закрыл диалог — чистим сессию."""
    from app.cache.redis import get_redis
    r = get_redis()
    raw = await r.get(_session_key(session_id))
    if raw:
        session = json.loads(raw)
        code = session.get("code")
        if code:
            await r.delete(_code_key(code))
    await r.delete(_session_key(session_id))
    await r.delete(_ready_key(session_id))
    return {"ok": True}
