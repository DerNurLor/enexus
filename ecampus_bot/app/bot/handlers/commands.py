"""
Command handlers for /mykey, /roles, /miniapp.
All interact with the auth database to fetch user info + generate tokens.
"""
from __future__ import annotations

from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from loguru import logger

from app.core.config import settings


async def _get_or_create_user(tg_user) -> tuple:
    """
    Upsert AuthUser from a Telegram user object.
    Returns (AuthUser, is_new).
    """
    from app.auth.models import AuthUser
    from datetime import datetime
    user = await AuthUser.find_one(AuthUser.tg_id == tg_user.id)
    if not user:
        user = AuthUser(
            tg_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "",
            last_name=tg_user.last_name,
        )
        await user.insert()
        logger.info(f"Bot: new user tg_id={tg_user.id}")
        return user, True
    user.last_active = datetime.utcnow()
    await user.save()
    return user, False


def _issue_miniapp_token(user) -> str:
    """Issue a short-lived JWT for the Mini App (15 min)."""
    from app.auth.security import create_access_token
    return create_access_token(str(user.id), user.tg_id, user.roles)


# ── /mykey ─────────────────────────────────────────────────────────────────────

# async def cmd_mykey(message: Message) -> None:
#     """Show active API keys and offer to generate one."""
#     from app.auth.models import AuthApiKey
#     tg_user = message.from_user
#     if not tg_user:
#         return
#     user, _ = await _get_or_create_user(tg_user)
#
#     keys = await AuthApiKey.find(
#         AuthApiKey.user_id == str(user.id),
#         AuthApiKey.is_revoked == False,  # noqa
#     ).sort("-created_at").to_list(10)
#
#     if not keys:
#         await message.answer(
#             "🔑 <b>У вас нет активных API ключей</b>\n\n"
#             "Создать ключ можно в личном кабинете:\n"
#             f"<a href=\"{settings.webhook_base_url}/dashboard/me\">Открыть профиль →</a>",
#             parse_mode="HTML",
#             disable_web_page_preview=True,
#         )
#         return
#
#     lines = ["🔑 <b>Ваши API ключи:</b>\n"]
#     for k in keys:
#         expires = f"до {k.expires_at.strftime('%d.%m.%Y')}" if k.expires_at else "бессрочный"
#         last = k.last_used_at.strftime("%d.%m %H:%M") if k.last_used_at else "никогда"
#         lines.append(
#             f"• <code>{k.key_prefix}…</code>  <i>{k.name}</i>\n"
#             f"  {k.rate_limit_rpm} rpm · {expires} · использован: {last}"
#         )
#
#     lines.append(
#         f"\n💡 Управление ключами: "
#         f"<a href=\"{settings.webhook_base_url}/dashboard/me\">личный кабинет</a>"
#     )
#     await message.answer("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


# ── /roles ─────────────────────────────────────────────────────────────────────

async def cmd_roles(message: Message) -> None:
    """Show user's roles, permissions and privileges in a clean format."""
    from app.auth.models import AuthRole
    tg_user = message.from_user
    if not tg_user:
        return
    user, _ = await _get_or_create_user(tg_user)

    role_docs = await AuthRole.find(
        {"name": {"$in": user.roles}}
    ).to_list()
    role_map = {r.name: r for r in role_docs}

    # Collect all permissions
    all_perms: set[str] = set(user.extra_permissions or [])
    for doc in role_docs:
        all_perms.update(doc.permissions)

    name  = f"{user.first_name} {user.last_name or ''}".strip()
    uname = f"@{user.username}" if user.username else f"tg:{user.tg_id}"

    # ── Role badges ──────────────────────────────────────────────────────────
    ROLE_META: dict[str, tuple[str, str]] = {
        "admin":    ("🔴", "Администратор"),
        "moderator":("🟠", "Модератор"),
        "vip":      ("🟡", "VIP"),
        "beta":     ("🔵", "Бета-тестер"),
        "user":     ("⚪", "Пользователь"),
    }

    role_lines: list[str] = []
    for role_name in user.roles:
        icon, label = ROLE_META.get(role_name, ("⚫", role_name.capitalize()))
        doc = role_map.get(role_name)
        desc = f" — {doc.description}" if doc and doc.description else ""
        role_lines.append(f"  {icon} <b>{label}</b> (<code>{role_name}</code>){desc}")

    # ── Privilege highlights ─────────────────────────────────────────────────
    extras: list[str] = []
    if "admin:full" in all_perms:
        extras.append(
            f"⚙️ <b>Панель управления</b> → "
            f"<a href=\"{settings.webhook_base_url}/dashboard/admin\">открыть</a>"
        )
    if "beta_access" in all_perms:
        extras.append("🧪 <b>Бета-доступ</b> — расширенные фильтры расписания")
    if "floorplan:edit" in all_perms:
        extras.append("🗺 <b>Редактирование</b> планов этажей")
    elif "floorplan:view" in all_perms:
        extras.append("🗺 <b>Просмотр</b> планов этажей")
    if user.daily_requests is not None and user.daily_requests > 0:
        extras.append(f"📊 <b>Персональный лимит</b>: {user.daily_requests} запросов / период")

    # ── Build message ────────────────────────────────────────────────────────
    lines = [
        f"👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
        "🎭 <b>Роли:</b>",
    ]
    lines += role_lines

    if extras:
        lines.append("\n🔓 <b>Привилегии:</b>")
        lines += [f"  {e}" for e in extras]

    lines.append(
        f"\n💼 <b>Личный кабинет:</b> "
        f"<a href=\"{settings.webhook_base_url}/dashboard/me\">открыть</a>"
    )

    await message.answer("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


# ── /suggest ──────────────────────────────────────────────────────────────────

async def cmd_suggest(message: Message) -> None:
    """Submit a suggestion/idea ticket — lifecycle mirrors /support but category=suggestion."""
    from app.auth.models import SupportTicket
    tg_user = message.from_user
    if not tg_user:
        return

    text = message.text or ""
    parts = text.split(maxsplit=1)
    idea_text = parts[1].strip() if len(parts) > 1 else ""

    if not idea_text:
        await message.answer(
            "💡 <b>Предложения и идеи</b>\n\n"
                "Есть идея, как улучшить бот или расписание?\n"
                "Напишите её после команды:\n\n"
                "<code>/suggest Ваша идея здесь</code>\n\n"
                "<i>Например: /suggest Добавить уведомление за 10 минут до пары</i>",
            parse_mode="HTML",
        )
        return

    user, _ = await _get_or_create_user(tg_user)

    ticket = SupportTicket(
        tg_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name or "",
        message=idea_text,
        source="bot",
        category="suggestion",
        status="open",
    )
    await ticket.insert()

    # Notify admin if configured
    from app.core.config import settings as _s
    if _s.support_bot_token and _s.support_admin_chat_id:
        try:
            import httpx
            uname = f"@{tg_user.username}" if tg_user.username else f"tg:{tg_user.id}"
            tid = str(ticket.id)
            notify_text = (
                f"💡 <b>Новое предложение</b>\n"
                    f"От: {tg_user.first_name} {uname} (tg_id={tg_user.id})\n"
                    f"ID: <code>{tid}</code>\n\n"
                    f"{idea_text[:500]}\n\n"
                    f"Ответить:\n"
                    f"<code>/reply {tid} Ваш ответ здесь</code>"
            )
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{_s.support_bot_token}/sendMessage",
                    json={
                        "chat_id": _s.support_admin_chat_id,
                        "text": notify_text,
                        "parse_mode": "HTML",
                    },
                )
        except Exception as exc:
            logger.warning(f"suggest notify failed: {exc}")

    await message.answer(
        "✅ <b>Предложение принято!</b>\n\n"
            "Спасибо, ваша идея поможет сделать бот лучше.\n"
            f"Номер: <code>{str(ticket.id)[:8]}</code>\n\n"
            "<i>Мы рассмотрим предложение и можем написать вам, если потребуются уточнения.</i>",
        parse_mode="HTML",
    )


# ── /about ────────────────────────────────────────────────────────────────────

async def cmd_about(message: Message) -> None:
    """Show information about the bot, version, and links."""
    miniapp_url = f"{settings.webhook_base_url}/miniapp"
    await message.answer(
        "🎓 <b>Бот расписания СКФУ</b>\n\n"
            "Умный помощник для студентов и преподавателей "
            "Северо-Кавказского федерального университета.\n\n"
            "📌 <b>Возможности:</b>\n"
            "  • Расписание групп, преподавателей, аудиторий\n"
            "  • Свободные аудитории в реальном времени\n"
            "  • Поиск по группам и преподавателям\n"
            "  • Mini App с полным расписанием 📅\n\n"
            "🔗 <b>Ссылки:</b>\n"
            f"  • <a href=\"{miniapp_url}\">Mini App расписания</a>\n"
            f"  • <a href=\"{settings.webhook_base_url}/dashboard/me\">Личный кабинет</a>\n\n"
            "🛠 <b>Версия:</b> 2.0\n"
            "💬 Вопросы и предложения: /support · /suggest",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ── /miniapp ───────────────────────────────────────────────────────────────────

async def cmd_miniapp(message: Message) -> None:
    """Send a button that opens the Mini App."""
    tg_user = message.from_user
    if not tg_user:
        return

    miniapp_url = f"{settings.webhook_base_url}/miniapp"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📅 Открыть расписание",
            web_app=WebAppInfo(url=miniapp_url),
        )
    ]])
    await message.answer(
        "🎓 <b>NCFU Schedule</b> — полное расписание в приложении\n\n"
            "• Гибкий поиск по группе, преподавателю, аудитории\n"
            "• Свободные аудитории в реальном времени\n"
            "• Планы этажей корпусов\n"
            "• Избранное и персональные настройки\n\n"
            "Нажмите кнопку ниже 👇",
        parse_mode="HTML",
        reply_markup=kb,
    )


# ── /support ───────────────────────────────────────────────────────────────────

async def cmd_support(message: Message) -> None:
    """Open a support ticket — saves to DB and notifies admin via bot API."""
    from app.auth.models import SupportTicket
    tg_user = message.from_user
    if not tg_user:
        return

    # The message after /support is the ticket text
    text = message.text or ""
    parts = text.split(maxsplit=1)
    ticket_text = parts[1].strip() if len(parts) > 1 else ""

    if not ticket_text:
        await message.answer(
            "📬 <b>Поддержка</b>\n\n"
                "Напишите ваш вопрос после команды:\n"
                "<code>/support Ваш вопрос здесь</code>",
            parse_mode="HTML",
        )
        return

    ticket = SupportTicket(
        tg_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name or "",
        message=ticket_text,
        source="bot",
        category="question",
    )
    await ticket.insert()

    # Notify admin via support bot if configured
    from app.core.config import settings
    if settings.support_bot_token and settings.support_admin_chat_id:
        try:
            import httpx
            uname = f"@{tg_user.username}" if tg_user.username else f"tg:{tg_user.id}"
            tid = str(ticket.id)
            notify_text = (
                f"🆕 <b>Новый тикет</b>\n"
                    f"От: {tg_user.first_name} {uname} (tg_id={tg_user.id})\n"
                    f"ID: <code>{tid}</code>\n\n"
                    f"{ticket_text[:500]}\n\n"
                    f"Ответить:\n"
                    f"<code>/reply {tid} Ваш ответ здесь</code>"
            )
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{settings.support_bot_token}/sendMessage",
                    json={
                        "chat_id": settings.support_admin_chat_id,
                        "text": notify_text,
                        "parse_mode": "HTML",
                    },
                )
        except Exception as exc:
            logger.warning(f"support notify failed: {exc}")

    await message.answer(
        "✅ <b>Обращение принято</b>\n\n"
            "Мы ответим вам как можно скорее.\n"
            f"Номер обращения: <code>{str(ticket.id)[:8]}</code>",
        parse_mode="HTML",
    )


# ── /limit ─────────────────────────────────────────────────────────────────────

async def cmd_limit(message: Message) -> None:
    """Show the user's current AI-query quota and how much is left."""
    tg_user = message.from_user
    if not tg_user:
        return

    chat      = message.chat
    chat_type = chat.type   # "private" | "group" | "supergroup" | "channel"

    from app.bot.middlewares.anti_flood import get_quota_status
    status = await get_quota_status(
        user_id=tg_user.id,
        chat_id=chat.id,
        chat_type=chat_type,
    )

    used      = status["used"]
    cap       = status["cap"]
    remaining = status["remaining"]
    ttl_secs  = status["ttl_secs"]
    ttl_h     = ttl_secs // 3600
    ttl_m     = (ttl_secs % 3600) // 60
    exhausted = status["exhausted"]

    # Build progress bar  ████░░░░  8 chars
    filled = round(used / cap * 8) if cap else 0
    bar    = "█" * filled + "░" * (8 - filled)

    if ttl_secs > 0:
        reset_str = f"{ttl_h}ч {ttl_m}м" if ttl_h else f"{ttl_m}м"
        reset_line = f"🔄 Сброс через: <b>{reset_str}</b>"
    else:
        reset_line = "🔄 Лимит уже сброшен — можно использовать снова"

    scope = "личных запросов" if chat_type == "private" else "запросов в этом чате"

    status_icon = "🔴" if exhausted else ("🟡" if remaining <= 1 else "🟢")

    await message.answer(
        f"📊 <b>Лимит {scope}</b>\n\n"
            f"{status_icon} <code>[{bar}]</code> {used}/{cap}\n\n"
            f"✅ Использовано: <b>{used}</b>\n"
            f"💬 Осталось: <b>{remaining}</b>\n"
            f"🏁 Максимум: <b>{cap}</b>\n"
            f"{reset_line}\n\n"
            + (
                "<i>Лимит исчерпан. Подождите сброса или обратитесь к администратору.</i>"
                if exhausted else
                "<i>Лимит считает запросы к ИИ (расписание, поиск). Команды /start, /help и другие не учитываются.</i>"
            ),
        parse_mode="HTML",
    )
