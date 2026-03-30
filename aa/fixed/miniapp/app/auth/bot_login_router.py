"""
auth/bot_login_router.py
Обмен одноразового токена от бота на JWT.

ИСПРАВЛЕНИЯ:
  [F1] decode_access_token() использовался для декодирования refresh_token.
       Функция называется decode_ACCESS_token, но применялась к refresh token.
       Это не вызывает ошибку (оба используют HS256), но:
       а) запутывает читателей кода;
       б) в будущем если алгоритм access/refresh tokens разойдётся — сломается молча.
       Переименовано в decode_token() через алиас для ясности.
  [F2] При ошибке декодирования refresh token (например, истёк) исключение
       поглощалось через `or {}` — это скрывало проблемы. Добавлено явное логирование.
  [F3] redis_key использует body.token напрямую — добавлена проверка формата токена
       для предотвращения Redis key injection (хотя min_length=10 уже ограничивает).
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from loguru import logger
from app.auth.models import AuthUser
from app.auth.security import create_access_token, create_refresh_token, decode_access_token
from app.auth.router import TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# [F1] Алиас для ясности — используется для ОБОИХ типов токенов (access и refresh)
# Оба используют одну функцию декодирования т.к. подписаны одним ключом
_decode_token = decode_access_token

# [F3] Допустимый формат одноразового токена от бота (hex или urlsafe base64)
_BOT_TOKEN_PATTERN = re.compile(r'^[A-Za-z0-9_\-]{10,128}$')


class BotTokenExchangeRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=128)


@router.post("/bot/exchange", response_model=TokenResponse)
async def bot_token_exchange(body: BotTokenExchangeRequest) -> TokenResponse:
    # [F3] Валидация формата токена перед обращением к Redis
    if not _BOT_TOKEN_PATTERN.match(body.token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный формат токена.")

    try:
        from app.cache.redis import get_redis
        r = get_redis()
        redis_key = f"bot:login:{body.token}"
        raw = await r.get(redis_key)
        if not raw:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен недействителен или истёк.")
        await r.delete(redis_key)
        payload = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        tg_id = payload["tg_id"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bot token exchange error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера.")

    user = await AuthUser.find_one(AuthUser.tg_id == tg_id)
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден.")
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован.")

    await user.set({"last_active": datetime.now(timezone.utc)})

    access_token  = create_access_token(str(user.id), user.tg_id, user.roles)
    refresh_token = create_refresh_token(str(user.id), user.tg_id)

    # Сохраняем JTI в Redis — без этого рефреш не работает
    try:
        # [F1][F2] Явно обрабатываем ошибку декодирования
        refresh_payload = _decode_token(refresh_token)
        jti = refresh_payload.get("jti", "")
        if jti:
            r = get_redis()
            await r.setex(f"refresh:jti:{jti}", 86400 * 31, str(user.id))
            await r.setex(f"refresh:user:{user.id}", 86400 * 31, jti)
    except Exception as e:
        logger.warning(f"Failed to store refresh JTI for tg_id={tg_id}: {e}")

    logger.info(f"Bot token exchange success tg_id={tg_id}")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
