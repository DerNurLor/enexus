"""
auth/bot_login_router.py
Обмен одноразового токена от бота на JWT.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from loguru import logger
from app.auth.models import AuthUser
from app.auth.security import create_access_token, create_refresh_token, decode_access_token
from app.auth.router import TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

class BotTokenExchangeRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=128)

@router.post("/bot/exchange", response_model=TokenResponse)
async def bot_token_exchange(body: BotTokenExchangeRequest) -> TokenResponse:
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
        refresh_payload = decode_access_token(refresh_token) or {}
        jti = refresh_payload.get("jti", "")
        if jti:
            r = get_redis()
            await r.setex(f"refresh:jti:{jti}", 86400 * 31, str(user.id))
            await r.setex(f"refresh:user:{user.id}", 86400 * 31, jti)
    except Exception as e:
        logger.warning(f"Failed to store refresh JTI: {e}")

    logger.info(f"Bot token exchange success tg_id={tg_id}")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
