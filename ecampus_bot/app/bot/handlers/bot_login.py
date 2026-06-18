"""
handlers/bot_login.py

Авторизация через числовой код — новый поток.

Поток:
  1. Сайт показывает 6-значный код пользователю
  2. Пользователь пишет этот код боту (или /login XXXXXX)
  3. Бот проверяет код через API → спрашивает подтвердить
  4. Пользователь нажимает «✅ Подтвердить»
  5. Бот вызывает API confirm → сайт автоматически входит

Команды:
  /start login    — старый поток (fallback, оставлен для совместимости)
  /login          — показывает инструкцию
  Любые 6 цифр   — обрабатываем как код входа
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

import httpx
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from loguru import logger

from app.core.config import settings
from app.i18n import t, get_user_lang, DEFAULT_LANG


# ── Callback data ─────────────────────────────────────────────────────────────

class LoginConfirmCallback(CallbackData, prefix="login"):
    action:     str   # "confirm" | "cancel"
    session_id: str


# ── Internal API helper ───────────────────────────────────────────────────────

def _api_base() -> str:
    """URL бэкенда для внутренних вызовов."""
    backend_url = getattr(settings, "backend_url", "") or "http://backend:8000"
    return backend_url.rstrip("/")


def _bot_secret() -> str:
    return getattr(settings, "bot_api_secret", "") or ""


async def _api_post(path: str, data: dict) -> dict | None:
    """POST к бэкенд API с внутренним секретом."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{_api_base()}{path}",
                json={**data, "bot_secret": _bot_secret()},
            )
            if resp.is_success:
                return resp.json()
            logger.warning(f"API {path} → {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as exc:
        logger.error(f"API call failed {path}: {exc}")
        return None


# ── Handlers ──────────────────────────────────────────────────────────────────

async def cmd_login(message: Message) -> None:
    """
    /login — показывает инструкцию как войти на сайт.
    """
    web_url = _get_web_url()
    await message.answer(
        "🔐 <b>Вход на сайт</b>\n\n"
        f"1. Откройте <a href=\"{web_url}/profile\">{web_url}/profile</a>\n"
        "2. Нажмите <b>«Войти через Telegram»</b>\n"
        "3. Вам покажут <b>6-значный код</b>\n"
        "4. Отправьте этот код мне\n"
        "5. Подтвердите вход — страница обновится автоматически\n\n"
        "💡 Или просто напишите мне 6-значный код прямо сейчас.",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def cmd_login(message: Message) -> None:
    """
    /login — показывает инструкцию как войти на сайт.
    """
    web_url = _get_web_url()
    lang = await get_user_lang(message.from_user.id) if message.from_user else DEFAULT_LANG
    await message.answer(
        t("login.instructions", lang, web_url=web_url),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def cmd_code(message: Message) -> None:
    """
    /code XXXXXX — ввод 6-буквенного кода для входа на сайт.
    Вынесен в отдельную команду чтобы middleware не считал это AI-запросом.
    """
    tg_user = message.from_user
    if not tg_user:
        return
    lang = await get_user_lang(tg_user.id)

    # Извлекаем код из аргументов команды
    parts = (message.text or "").strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(t("login.code_missing", lang), parse_mode="HTML")
        return

    code = parts[1].strip().upper()  # приводим к верхнему регистру на всякий случай

    if not re.fullmatch(r"[A-Z0-9]{6}", code):
        await message.answer(t("login.code_invalid_format", lang), parse_mode="HTML")
        return

    await _process_code(message, tg_user, code)


async def handle_login_code(message: Message) -> None:
    """
    Fallback: пользователь написал 6 букв без команды (обратная совместимость).
    """
    tg_user = message.from_user
    if not tg_user:
        return

    code = (message.text or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{6}", code):
        return

    await _process_code(message, tg_user, code)


async def _process_code(message: Message, tg_user, code: str) -> None:
    """Общая логика проверки кода и запроса подтверждения."""
    lang = await get_user_lang(tg_user.id)

    # Убеждаемся что пользователь есть в БД
    try:
        from app.bot.handlers.commands import _get_or_create_user
        user, _ = await _get_or_create_user(tg_user)
        if user.is_blocked:
            await message.answer(t("login.account_blocked", lang))
            return
    except Exception as exc:
        logger.error(f"Failed to get/create user for tg_id={tg_user.id}: {exc}")
        await message.answer(t("login.server_error", lang))
        return

    # Проверяем код через API
    result = await _api_post("/auth/code/verify", {
        "code":  code,
        "tg_id": tg_user.id,
    })

    if not result or not result.get("ok"):
        error = result.get("detail") if result else None
        error = error or (t("login.code_error_default", lang) if result else t("login.code_error_server", lang))
        await message.answer(t("login.code_error", lang, error=error), parse_mode="HTML")
        return

    session_id = result.get("session_id", "")
    name = tg_user.first_name or t("login.default_name", lang)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t("login.confirm_button", lang),
            callback_data=LoginConfirmCallback(action="confirm", session_id=session_id).pack(),
        ),
        InlineKeyboardButton(
            text=t("login.cancel_button", lang),
            callback_data=LoginConfirmCallback(action="cancel", session_id=session_id).pack(),
        ),
    ]])

    await message.answer(
        t("login.confirm_prompt", lang, name=name),
        parse_mode="HTML",
        reply_markup=kb,
    )


async def handle_login_callback(callback: CallbackQuery) -> None:
    """
    Пользователь нажал «Подтвердить» или «Отмена».
    """
    if not callback.message or not callback.from_user:
        await callback.answer()
        return

    data = LoginConfirmCallback.unpack(callback.data)
    tg_id = callback.from_user.id
    lang = await get_user_lang(tg_id)

    if data.action == "cancel":
        # Отменяем сессию на сервере
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.delete(
                    f"{_api_base()}/auth/code/cancel/{data.session_id}"
                )
        except Exception:
            pass

        await callback.message.edit_text(t("login.cancelled", lang), parse_mode="HTML")
        await callback.answer(t("login.cancelled_toast", lang))
        return

    # Подтверждаем вход
    result = await _api_post("/auth/code/confirm", {
        "session_id": data.session_id,
        "tg_id":      tg_id,
    })

    if not result or not result.get("ok"):
        await callback.message.edit_text(t("login.confirm_error", lang), parse_mode="HTML")
        await callback.answer(t("login.confirm_error_toast", lang))
        return

    await callback.message.edit_text(t("login.confirmed", lang), parse_mode="HTML")
    await callback.answer(t("login.confirmed_toast", lang))


# ── Fallback: старый /start login (совместимость) ─────────────────────────────

async def cmd_start_login(message: Message, token_param: str) -> None:
    """
    Старый поток /start login — показываем инструкцию с новым кодовым методом.
    Оставлен для совместимости со старыми ссылками.
    """
    web_url = _get_web_url()
    lang = await get_user_lang(message.from_user.id) if message.from_user else DEFAULT_LANG
    name = message.from_user.first_name if message.from_user else t("login.default_name", lang)

    await message.answer(
        t("start.login_welcome", lang, name=name, web_url=web_url),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


def _get_web_url() -> str:
    url = getattr(settings, "web_url", "") or getattr(settings, "webhook_base_url", "")
    return url.replace("/miniapp", "").rstrip("/")
