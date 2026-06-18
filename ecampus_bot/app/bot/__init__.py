"""
Bot setup and lifecycle helpers called from main.py lifespan.
"""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from app.core.config import settings
from app.bot.router import router, get_bot_commands
from app.bot.middlewares import LoggingMiddleware, RateLimitMiddleware
from app.bot.middlewares.anti_flood import AntiFloodMiddleware, MessageLimitMiddleware
from app.i18n import SUPPORTED_LANGUAGES, DEFAULT_LANG

_bot: Bot | None = None
_dp:  Dispatcher | None = None


def get_bot() -> Bot:
    assert _bot is not None, "Bot not initialised"
    return _bot


def get_dp() -> Dispatcher:
    assert _dp is not None, "Dispatcher not initialised"
    return _dp


async def setup_bot() -> tuple[Bot, Dispatcher]:
    global _bot, _dp
    _bot = Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    _dp = Dispatcher()

    # ── Middleware stack (outermost first) ────────────────────────────────────
    # 1. Logging — always runs, even for rate-limited/blocked updates
    _dp.message.middleware(LoggingMiddleware())
    # 2. Anti-flood — drop spammers before they reach the AI handler
    _dp.message.middleware(AntiFloodMiddleware())
    # 3. Message quota — enforce per-chat/per-user daily limits
    _dp.message.middleware(MessageLimitMiddleware())
    # 4. Existing bot rate limiter (per-user sliding window, configurable RPM)
    _dp.message.middleware(RateLimitMiddleware())

    _dp.include_router(router)

    # ── Register the localized command menu for each supported language ───────
    try:
        await _bot.set_my_commands(get_bot_commands(DEFAULT_LANG))
        for lang in SUPPORTED_LANGUAGES:
            if lang == DEFAULT_LANG:
                continue
            await _bot.set_my_commands(get_bot_commands(lang), language_code=lang)
    except Exception as exc:
        logger.warning(f"set_my_commands failed: {exc}")

    webhook_url    = f"{settings.webhook_base_url}/webhook/telegram"
    webhook_secret = settings.telegram_webhook_secret.get_secret_value() or None

    await _bot.set_webhook(
        url=webhook_url,
        allowed_updates=["message", "my_chat_member", "callback_query"],
        drop_pending_updates=True,
        # Pass the secret so Telegram signs every update with
        # X-Telegram-Bot-Api-Secret-Token — verified in main.py webhook handler.
        secret_token=webhook_secret,
    )
    info = await _bot.get_webhook_info()
    logger.info(f"Webhook set to {info.url} (secret={'set' if webhook_secret else 'unset'})")
    return _bot, _dp


async def teardown_bot() -> None:
    global _bot
    if _bot:
        await _bot.delete_webhook()
        await _bot.session.close()
        logger.info("Bot webhook deleted.")
