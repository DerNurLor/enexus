"""
handlers/bot_login.py

Авторизация через бота — альтернатива Telegram Login Widget.

Поток:
  1. Пользователь на сайте нажимает «Войти через бота»
  2. Сайт редиректит на t.me/ncfu_schedule_bot?start=login
  3. Бот получает /start login → генерирует одноразовый токен (OTP)
  4. Бот показывает кнопку «Подтвердить вход» с URL сайта + токеном
  5. Пользователь нажимает кнопку → сайт вызывает /auth/bot/exchange
  6. Сервер проверяет токен, выдаёт JWT

Безопасность:
  - Токен одноразовый (удаляется после использования)
  - TTL токена — 5 минут
  - Токен привязан к tg_id пользователя
  - 32 байта случайных данных (256 бит энтропии)
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta

from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from app.core.config import settings


async def cmd_start_login(message: Message, token_param: str) -> None:
    """
    Обрабатывает /start login_XXXXX от пользователя который хочет войти через бота.
    Генерирует одноразовый токен и сохраняет его в Redis.
    """
    tg_user = message.from_user
    if not tg_user:
        return

    # Создаём или обновляем пользователя в БД
    from app.bot.handlers.commands import _get_or_create_user
    user, is_new = await _get_or_create_user(tg_user)

    if user.is_blocked:
        await message.answer("❌ Ваш аккаунт заблокирован.")
        return

    # Генерируем одноразовый токен
    otp = secrets.token_urlsafe(32)

    # Сохраняем в Redis с TTL 5 минут
    try:
        from app.cache.redis import get_redis
        r = get_redis()
        import json
        payload = json.dumps({
            "tg_id":      tg_user.id,
            "user_id":    str(user.id),
            "first_name": tg_user.first_name or "",
            "last_name":  tg_user.last_name or "",
            "username":   tg_user.username or "",
            "photo_url":  None,
            "roles":      user.roles,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await r.setex(f"bot:login:{otp}", 300, payload)  # 5 минут
        logger.info(f"Bot login OTP generated for tg_id={tg_user.id}")
    except Exception as e:
        logger.error(f"Redis error generating OTP: {e}")
        await message.answer("⚠️ Ошибка сервера. Попробуйте позже.")
        return

    # Определяем URL сайта
    web_url = getattr(settings, 'web_url', None) or getattr(settings, 'webhook_base_url', '')
    # Убираем /miniapp если есть, берём только базовый URL
    web_url = web_url.replace('/miniapp', '').rstrip('/')

    # Кнопка подтверждения — ведёт на сайт с токеном
    confirm_url = f"{web_url}/profile?bot_token={otp}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить вход", url=confirm_url)
    ]])

    name = tg_user.first_name or "пользователь"
    await message.answer(
        f"🔐 <b>Подтверждение входа</b>\n\n"
        f"Привет, {name}!\n\n"
        f"Нажмите кнопку ниже чтобы войти на сайт.\n"
        f"Ссылка действительна <b>5 минут</b>.\n\n"
        f"⚠️ Если вы не запрашивали вход — проигнорируйте это сообщение.",
        parse_mode="HTML",
        reply_markup=kb,
    )
