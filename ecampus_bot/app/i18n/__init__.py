"""
i18n/__init__.py — простой dict-based i18n для бота.

Почему не gettext/babel: всего ~100 ключей, gettext добавил бы .po/.mo
компиляцию и лишнюю инфраструктуру без реальной выгоды на таком объёме.

Использование:
    from app.i18n import t, get_user_lang
    lang = await get_user_lang(tg_id)
    await message.answer(t("start.greeting", lang, name=user.first_name))

Язык хранится в AuthUser.miniapp_settings["language"] — то же поле,
которое читают/пишут web и miniapp (см. /miniapp/api/settings), поэтому
выбор языка синхронен между всеми тремя поверхностями.
"""
from __future__ import annotations

from typing import Any

from .locales import LOCALES, DEFAULT_LANG, SUPPORTED_LANGUAGES, LANGUAGE_NAMES


def _resolve_telegram_lang(language_code: str | None) -> str:
    """Сопоставляет Telegram language_code (en-US, zh-Hans, …) с одним из наших кодов."""
    if not language_code:
        return DEFAULT_LANG
    code = language_code.lower().split("-")[0]
    return code if code in LOCALES else DEFAULT_LANG


async def get_user_lang(tg_id: int) -> str:
    """
    Возвращает язык пользователя:
    1. Явный выбор — miniapp_settings.language (через /language или сайт/miniapp)
    2. Иначе — Telegram language_code, если он среди поддерживаемых
    3. Иначе — DEFAULT_LANG (ru)
    """
    try:
        from app.auth.models import AuthUser
        user = await AuthUser.find_one(AuthUser.tg_id == tg_id)
        if not user:
            return DEFAULT_LANG
        explicit = (user.miniapp_settings or {}).get("language")
        if explicit and explicit in LOCALES:
            return explicit
        return _resolve_telegram_lang(user.language_code)
    except Exception:
        return DEFAULT_LANG


async def set_user_lang(tg_id: int, lang: str) -> bool:
    """Сохраняет выбор языка в miniapp_settings — видно сайту и miniapp."""
    if lang not in LOCALES:
        return False
    from app.auth.models import AuthUser
    user = await AuthUser.find_one(AuthUser.tg_id == tg_id)
    if not user:
        return False
    settings = dict(user.miniapp_settings or {})
    settings["language"] = lang
    user.miniapp_settings = settings
    await user.save()
    return True


def t(key: str, lang: str = DEFAULT_LANG, **kwargs: Any) -> str:
    """
    Возвращает локализованную строку по ключу (напр. "start.greeting").
    Падает на DEFAULT_LANG, если перевода нет, и на сам ключ, если его
    вообще нет ни в одной локали (чтобы не падать молча в проде).
    """
    table = LOCALES.get(lang, LOCALES[DEFAULT_LANG])
    template = table.get(key) or LOCALES[DEFAULT_LANG].get(key) or key
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


__all__ = [
    "t", "get_user_lang", "set_user_lang",
    "LOCALES", "DEFAULT_LANG", "SUPPORTED_LANGUAGES", "LANGUAGE_NAMES",
]
