"""
Эндпоинт для авторизации через Telegram Login Widget (обычный браузер).

Отличие от initData (Mini App):
- Mini App:     POST /auth/telegram/login    — принимает raw initData строку
- Login Widget: POST /auth/telegram/widget   — принимает JSON с id, hash, auth_date, ...

Безопасность (ГОСТ подход):
  [W1] Hash проверяется через HMAC-SHA256 по алгоритму Telegram
  [W2] auth_date проверяется — данные старше 24 часов отклоняются
  [W3] Все поля валидируются через Pydantic
  [W4] Те же rate limit, блокировка и логирование что и в /login
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from loguru import logger

from app.auth.models import AuthUser
from app.auth.security import create_access_token, create_refresh_token
from app.auth.router import TokenResponse  # переиспользуем схему ответа
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# Максимальный возраст данных авторизации (24 часа)
MAX_AUTH_AGE_SECONDS = 86_400


class TelegramWidgetAuthRequest(BaseModel):
    """Данные от Telegram Login Widget."""
    id:         int    = Field(..., description="Telegram user ID")
    first_name: str    = Field(..., max_length=256)
    last_name:  Optional[str] = Field(None, max_length=256)
    username:   Optional[str] = Field(None, max_length=256)
    photo_url:  Optional[str] = Field(None, max_length=512)
    auth_date:  int    = Field(..., description="Unix timestamp of auth")
    hash:       str    = Field(..., min_length=64, max_length=64, description="HMAC-SHA256 hash")


def _verify_telegram_widget_hash(data: TelegramWidgetAuthRequest, bot_token: str) -> bool:
    """
    Проверяет hash от Telegram Login Widget.

    Алгоритм (https://core.telegram.org/widgets/login):
      1. Собираем строку data_check_string из всех полей кроме hash, отсортированных по ключу
      2. secret_key = SHA256(bot_token)
      3. hash = HMAC-SHA256(data_check_string, secret_key)
    """
    # Собираем поля для проверки (все кроме hash)
    fields: dict[str, str] = {
        'id':         str(data.id),
        'first_name': data.first_name,
        'auth_date':  str(data.auth_date),
    }
    if data.last_name:  fields['last_name']  = data.last_name
    if data.username:   fields['username']   = data.username
    if data.photo_url:  fields['photo_url']  = data.photo_url

    # Строка для проверки: ключ=значение, отсортировано по ключу, разделитель \n
    data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(fields.items()))

    # secret = SHA256(bot_token)
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Вычисляем ожидаемый hash
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    # Сравниваем безопасно (защита от timing attack)
    return hmac.compare_digest(expected_hash, data.hash)


@router.post("/telegram/widget", response_model=TokenResponse)
async def telegram_widget_login(
    request: Request,
    body: TelegramWidgetAuthRequest,
) -> TokenResponse:
    """
    Авторизация через Telegram Login Widget для обычного браузера.
    Проверяет hash, создаёт/обновляет пользователя, выдаёт JWT.
    """
    # [W2] Проверяем свежесть данных
    age = int(time.time()) - body.auth_date
    if age > MAX_AUTH_AGE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Данные авторизации устарели ({age}s > {MAX_AUTH_AGE_SECONDS}s). Войдите снова.",
        )

    # [W1] Проверяем подпись
    bot_token = settings.telegram_bot_token.get_secret_value()
    if not _verify_telegram_widget_hash(body, bot_token):
        logger.warning(f"Widget auth: invalid hash for tg_id={body.id} ip={request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительная подпись Telegram. Попробуйте снова.",
        )

    # Находим или создаём пользователя
    user = await AuthUser.find_one(AuthUser.tg_id == body.id)
    if user is None:
        user = AuthUser(
            tg_id=body.id,
            first_name=body.first_name,
            last_name=body.last_name,
            username=body.username,
            photo_url=body.photo_url,
            roles=['user'],
        )
        await user.insert()
        logger.info(f"Widget auth: new user registered tg_id={body.id}")
    else:
        # Обновляем данные профиля
        update: dict = {}
        if body.first_name != user.first_name: update['first_name'] = body.first_name
        if body.last_name  != user.last_name:  update['last_name']  = body.last_name
        if body.username   != user.username:   update['username']   = body.username
        if body.photo_url  != user.photo_url:  update['photo_url']  = body.photo_url
        if update:
            await user.set(update)

    # Проверяем блокировку
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваша учётная запись заблокирована.",
        )

    # Выдаём токены
    access_token  = create_access_token(str(user.id), user.tg_id, user.roles)
    refresh_token = create_refresh_token(str(user.id), user.tg_id)

    logger.info(f"Widget auth: success tg_id={body.id} username={body.username}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
