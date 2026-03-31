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
    await message.answer(
        "🔐 <b>Вход на сайт</b>\n\n"
        f"1. Откройте <a href=\"{web_url}/profile\">{web_url}/profile</a>\n"
        "2. Нажмите <b>«Войти через Telegram»</b>\n"
        "3. Вам покажут <b>6-буквенный код</b> (заглавные латинские)\n"
        "4. Отправьте этот код командой <code>/code XXXXXX</code>\n"
        "5. Подтвердите вход — страница обновится автоматически\n\n"
        "💡 Или просто напишите <code>/code</code> и код через пробел.",
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

    # Извлекаем код из аргументов команды
    parts = (message.text or "").strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "❓ Укажи код после команды:\n"
            "<code>/code XXXXXX</code>\n\n"
            "Код отображается на сайте при нажатии «Войти через Telegram».",
            parse_mode="HTML",
        )
        return

    code = parts[1].strip().upper()  # приводим к верхнему регистру на всякий случай

    if not re.fullmatch(r"[A-Z0-9]{6}", code):
        await message.answer(
            "❌ Код должен состоять из <b>6 заглавных букв и цифр</b>.\n"
            "Пример: <code>/code ABCDEF</code>",
            parse_mode="HTML",
        )
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

    # Убеждаемся что пользователь есть в БД
    try:
        from app.bot.handlers.commands import _get_or_create_user
        user, _ = await _get_or_create_user(tg_user)
        if user.is_blocked:
            await message.answer("❌ Ваш аккаунт заблокирован.")
            return
    except Exception as exc:
        logger.error(f"Failed to get/create user for tg_id={tg_user.id}: {exc}")
        await message.answer("⚠️ Ошибка сервера. Попробуйте позже.")
        return

    # Проверяем код через API
    result = await _api_post("/auth/code/verify", {
        "code":  code,
        "tg_id": tg_user.id,
    })

    if not result or not result.get("ok"):
        error = result.get("detail", "Неверный или истёкший код") if result else "Ошибка сервера"
        await message.answer(
            f"❌ <b>{error}</b>\n\n"
            "Проверьте код на сайте и попробуйте снова.\n"
            "Код действителен <b>3 минуты</b>.",
            parse_mode="HTML",
        )
        return

    session_id = result.get("session_id", "")
    name = tg_user.first_name or "пользователь"

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Подтвердить вход",
            callback_data=LoginConfirmCallback(action="confirm", session_id=session_id).pack(),
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=LoginConfirmCallback(action="cancel", session_id=session_id).pack(),
        ),
    ]])

    await message.answer(
        f"🔐 <b>Подтверждение входа</b>\n\n"
        f"Привет, {name}! Кто-то входит на сайт с твоим аккаунтом.\n\n"
        f"Подтвердить вход?",
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

    if data.action == "cancel":
        # Отменяем сессию на сервере
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.delete(
                    f"{_api_base()}/auth/code/cancel/{data.session_id}"
                )
        except Exception:
            pass

        await callback.message.edit_text(
            "❌ <b>Вход отменён.</b>\n\n"
            "Если это были не вы — ничего страшного, ссылка уже недействительна.",
            parse_mode="HTML",
        )
        await callback.answer("Вход отменён")
        return

    # Подтверждаем вход
    result = await _api_post("/auth/code/confirm", {
        "session_id": data.session_id,
        "tg_id":      tg_id,
    })

    if not result or not result.get("ok"):
        await callback.message.edit_text(
            "⚠️ <b>Ошибка подтверждения.</b>\n\n"
            "Возможно, сессия истекла. Попробуйте войти снова.",
            parse_mode="HTML",
        )
        await callback.answer("Ошибка, попробуйте снова")
        return

    await callback.message.edit_text(
        "✅ <b>Вход подтверждён!</b>\n\n"
        "Страница на сайте обновится автоматически.",
        parse_mode="HTML",
    )
    await callback.answer("Вход выполнен ✅")


# ── Fallback: старый /start login (совместимость) ─────────────────────────────

async def cmd_start_login(message: Message, token_param: str) -> None:
    """
    Старый поток /start login — показываем инструкцию с новым кодовым методом.
    Оставлен для совместимости со старыми ссылками.
    """
    web_url = _get_web_url()
    name = message.from_user.first_name if message.from_user else "пользователь"

    await message.answer(
        f"👋 Привет, {name}!\n\n"
        "🔐 <b>Новый способ входа</b>\n\n"
        f"1. Откройте <a href=\"{web_url}/profile\">{web_url}/profile</a>\n"
        "2. Нажмите <b>«Войти через Telegram»</b>\n"
        "3. Отправьте мне показанный <b>6-значный код</b>\n"
        "4. Подтвердите — страница обновится сама ✨",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


def _get_web_url() -> str:
    url = getattr(settings, "web_url", "") or getattr(settings, "webhook_base_url", "")
    return url.replace("/miniapp", "").rstrip("/")
