"""
Aiogram router — registers all message/command handlers.

Every message type (text, photo, video, animation, sticker, voice,
video_note, audio, document) is stored to the conversations collection
via store_message().  This is done inside a dedicated catch-all
handler so media-only messages (no caption text) are still persisted
even if they don't trigger the AI handler.
"""
from __future__ import annotations

import asyncio

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (BotCommand, ChatMemberUpdated,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    Message as TelegramMessage, CallbackQuery)
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, MEMBER, ADMINISTRATOR, CREATOR
from app.core.config import settings
from app.models.conversation import Message as MessageModel

from app.bot.handlers.ai_handler import handle_message
from app.bot.handlers.commands  import cmd_roles, cmd_miniapp, cmd_limit
from app.bot.message_store import store_message, store_callback_choice, store_bot_reply, _entities_to_html
from datetime import datetime, timezone
import logging

router = Router(name="ncfu_bot")
logger = logging.getLogger(__name__)


# ── Bot added to a group — send welcome message ────────────────────────────────

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER | ADMINISTRATOR | CREATOR))
async def bot_added_to_group(event: ChatMemberUpdated) -> None:
    """Greet the group when the bot is added, explain commands and show Mini App button."""
    if event.chat.type not in ('group', 'supergroup'):
        return
    try:
        chat    = event.chat
        inviter = event.from_user

        # ── Reset group quota so re-invited bot starts with a fresh counter ──
        try:
            from app.cache.redis import get_redis
            r = get_redis()
            await r.delete(f'quota:{chat.id}')
        except Exception as _re:
            logger.warning(f'quota reset on group add failed: {_re}')

        # ── Upsert ChatSettings with the group's real title/username ─────────
        try:
            from app.bot.message_store import _upsert_chat_meta
            await _upsert_chat_meta(
                chat_id=chat.id,
                chat_key=f'{chat.id}:0',
                chat_type=str(chat.type),
                title=chat.title,
                username=getattr(chat, 'username', None),  # group @username only
            )
        except Exception as _ce:
            logger.warning(f'chat meta upsert on add failed: {_ce}')

        # ── Upsert inviter's AuthUser profile ─────────────────────────────────
        if inviter:
            try:
                from app.bot.handlers.ai_handler import _upsert_user
                await _upsert_user(inviter)
            except Exception as _ue:
                logger.warning(f'user upsert on group add failed: {_ue}')

        bot_username = (await event.bot.get_me()).username
        miniapp_url  = f"{settings.webhook_base_url}/miniapp"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📅 Открыть расписание", web_app=WebAppInfo(url=miniapp_url))
        ]])
        chat_title = chat.title or "эту группу"
        await event.bot.send_message(
            chat_id=chat.id,
            text=(
                f"👋 Привет! Рад присоединиться к <b>{chat_title}</b>!\n\n"
                "📌 <b>Что я умею:</b>\n"
                "  • Расписание группы, преподавателя, аудитории\n"
                "  • Свободные аудитории прямо сейчас\n"
                "  • Поиск по преподавателям и группам\n\n"
                "💬 <b>Как обращаться:</b>\n"
                f"  Упомяните меня: <code>@{bot_username} расписание ИСС-б-о-22-3</code>\n"
                "  Или используйте команды:\n"
                "  /help — все возможности\n"
                "  /miniapp — расписание в приложении 📅\n\n"
                "🔕 <i>Я не слежу за общим чатом — отвечаю только на упоминания и команды.</i>"
            ),
            parse_mode="HTML",
            reply_markup=kb,
        )
    except Exception as exc:
        logger.warning(f"bot_added_to_group welcome failed: {exc}")


# ── /start ─────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: TelegramMessage) -> None:
    from app.bot.handlers.commands import _get_or_create_user
    if message.from_user:
        await _get_or_create_user(message.from_user)
    # Сохраняем входящее сообщение пользователя (/start)
    asyncio.ensure_future(store_message(message, role="user"))

    sent = await message.answer(
        "👋 Привет! Я бот расписания СКФУ.\n\n"
            "Спрашивай на естественном русском языке:\n"
            "  • <i>Расписание ИСС-б-о-22-3 на эту неделю</i>\n"
            "  • <i>Где пара через 5 минут у Подзолко?</i>\n"
            "  • <i>Свободные аудитории в корпусе 11</i>\n"
            "  • <i>Что сейчас у группы АИС-б-о-25-1?</i>\n\n"
            "📋 <b>Команды:</b>\n"
            "  /help    — полная справка по возможностям\n"
            "  /miniapp — расписание в приложении 📅\n"
            "  /limit   — ваш лимит запросов\n"
            "  /roles   — ваши роли и привилегии\n"
            "  /support — написать в поддержку\n"
            "  /suggest — предложить улучшение\n"
            "  /about   — о боте",
        parse_mode="HTML",
    )
    # Сохраняем ответ бота — Telegram не присылает Update на исходящие сообщения
    asyncio.ensure_future(store_message(sent, role="bot"))


# ── /help ──────────────────────────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message, role="user"))
    sent = await message.answer(
        "📖 <b>Справка по боту расписания СКФУ</b>\n\n"
            "Просто напиши запрос на естественном языке:\n\n"
            "📅 <b>Расписание группы:</b>\n"
            "  <i>Расписание ИСС-б-о-22-3</i>\n"
            "  <i>Что у группы АИС25 завтра?</i>\n"
            "  <i>Пары на эту неделю у группы МАТ-22</i>\n\n"
            "👤 <b>Преподаватель:</b>\n"
            "  <i>Где Подзолко сейчас?</i>\n"
            "  <i>Расписание Иванова на завтра</i>\n\n"
            "🚪 <b>Аудитории:</b>\n"
            "  <i>Свободные аудитории прямо сейчас</i>\n"
            "  <i>Что сейчас в аудитории 305 корпуса 2?</i>\n"
            "  <i>Свободные аудитории в корпусе 11 с 14:00</i>\n\n"
            "🔍 <b>Поиск:</b>\n"
            "  <i>Найди группу ИСС</i>  ·  <i>Найди Петрова</i>\n\n"
            "📋 <b>Команды:</b>\n"
            "  /miniapp — открыть расписание в приложении 📅\n"
            "  /limit   — узнать остаток лимита запросов\n"
            "  /roles   — ваши роли и права доступа\n"
            "  /support — написать в поддержку\n"
            "  /suggest — предложить идею или улучшение\n"
            "  /about   — информация о боте\n"
            "  /start   — начало работы\n"
            "  /help    — эта справка\n\n"
            "💡 <i>В группах обращайтесь к боту через упоминание: @botname запрос</i>",
        parse_mode="HTML",
    )
    asyncio.ensure_future(store_message(sent, role="bot"))


# ── Other commands ─────────────────────────────────────────────────────────────

@router.message(Command("mykey"))
async def handle_mykey(message: TelegramMessage) -> None:
    # /mykey is disabled
    await message.answer("Команда /mykey отключена.")


@router.message(Command("roles"))
async def handle_roles(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message, role="user"))
    sent = await cmd_roles(message)
    if sent:
        asyncio.ensure_future(store_message(sent, role="bot"))


@router.message(Command("miniapp"))
async def handle_miniapp(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message, role="user"))
    sent = await cmd_miniapp(message)
    if sent:
        asyncio.ensure_future(store_message(sent, role="bot"))


@router.message(Command("limit"))
async def handle_limit(message: TelegramMessage) -> None:
    await cmd_limit(message)


@router.message(F.chat.type.in_({'group', 'supergroup'}))
async def handle_group_message(message: TelegramMessage) -> None:
    """
    Store every group message, but only respond when the bot is
    explicitly addressed — via mention, reply-to-bot, or a command.
    This avoids the bot flooding active group chats with unsolicited answers.
    """
    asyncio.ensure_future(store_message(message, role='user'))
    if message.from_user:
        from app.bot.handlers.ai_handler import _upsert_user
        asyncio.ensure_future(_upsert_user(message.from_user))

    text = message.text or message.caption or ''
    if not text.strip():
        return   # media-only with no caption — just store, never respond

    # Lazy-fetch bot username once per process
    bot_me = await message.bot.get_me()
    bot_username = (bot_me.username or '').lower()

    def _is_addressed() -> bool:
        t = text.lower()
        # 1. Direct command (/help, /start, /help@botname)
        if t.startswith('/'):
            return True
        # 2. @mention anywhere in message
        if bot_username and f'@{bot_username}' in t:
            return True
        # 3. Reply to a bot message
        if message.reply_to_message and message.reply_to_message.from_user:
            if message.reply_to_message.from_user.id == bot_me.id:
                return True
        # 4. Entity-based mention (catches @BotName even mid-sentence)
        for ent in (message.entities or message.caption_entities or []):
            if ent.type.value in ('mention', 'bot_command'):
                chunk = text[ent.offset: ent.offset + ent.length].lower()
                if bot_username and bot_username in chunk:
                    return True
                if ent.type.value == 'bot_command':
                    return True   # any /command in group is addressed to bot
        return False

    if _is_addressed():
        # Strip the bot mention from text so the AI gets clean input
        clean_text = text.replace(f'@{bot_me.username}', '').strip() if bot_me.username else text
        if clean_text:
            message._text_override = clean_text  # noqa: used by handle_message below
        await handle_message(message)

@router.channel_post()
async def handle_channel_post(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message, role='channel'))

@router.edited_message()
async def handle_edited(message: TelegramMessage) -> None:
    # Обновить текст существующего документа вместо создания нового
    asyncio.ensure_future(_update_edited_message(message))

# В message_store.py — обновление отредактированного сообщения
async def _update_edited_message(msg: TelegramMessage) -> None:
    try:
        doc = await MessageModel.find_one(
            MessageModel.chat_id == msg.chat.id,
            MessageModel.message_id == msg.message_id
        )
        if doc:
            doc.text = msg.text or msg.caption or ''
            doc.html_text = _entities_to_html(
                doc.text, msg.entities or [])
            doc.edited_at = datetime.utcnow()
            await doc.save()
    except Exception as exc:
        logger.warning(f'_update_edited_message failed: {exc}')


# ── Inline keyboard callback — page navigation ─────────────────────────────────

@router.callback_query(F.data.startswith("pg:"))
async def cb_page_nav(cb: CallbackQuery) -> None:
    """Handle ◀/▶ buttons for paged schedule responses."""
    await cb.answer()
    # callback_data format: "pg:{page_key}:{idx}:{total}"
    # page_key itself contains colons (e.g. "bot:pages:123:abc"), so we can't
    # naively split on ":" — instead strip the "pg:" prefix then rsplit from the right.
    data = cb.data[3:]  # strip leading "pg:"
    try:
        rest, total_str = data.rsplit(":", 1)
        page_key, idx_str = rest.rsplit(":", 1)
        idx   = int(idx_str)
        total = int(total_str)
    except (ValueError, AttributeError):
        return

    from app.bot.handlers.ai_handler import _load_pages, _make_nav_kb, _add_feedback_row
    pages = await _load_pages(page_key)
    if not pages:
        await cb.message.edit_text("⏱ Данные устарели. Повторите запрос.", reply_markup=None)
        return

    idx = max(0, min(idx, len(pages) - 1))
    kb  = _make_nav_kb(page_key, idx, len(pages))

    # Re-attach feedback row if it was present before (check existing kb)
    current_kb = cb.message.reply_markup
    has_feedback = current_kb and any(
        any(btn.callback_data and btn.callback_data.startswith("fb:") for btn in row)
        for row in (current_kb.inline_keyboard or [])
    )
    if has_feedback:
        kb = _add_feedback_row(kb, cb.message.chat.id, cb.message.message_id)

    text = pages[idx] + f"\n\n<i>День {idx+1} из {len(pages)}</i>"
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass  # message unchanged — ignore


@router.callback_query(F.data == "pg_noop")
async def cb_noop(cb: CallbackQuery) -> None:
    await cb.answer()


@router.callback_query(F.data.startswith("dis:"))
async def cb_disambig(cb: CallbackQuery) -> None:
    """
    Handle group/room disambiguation button press.
    callback_data: "dis:{redis_key}:{item_id}"
    """
    await cb.answer()
    try:
        # callback_data: "dis:{redis_key}:{item_id}"
        # redis_key contains colons, so we must split from the RIGHT.
        after_prefix = cb.data[4:]   # strip "dis:"
        key, id_str  = after_prefix.rsplit(":", 1)
        # id_str should be a plain integer (group_id or room_id).
        # Guard against accidental "None" strings if a candidate had a null id.
        if not id_str or id_str == "None":
            raise ValueError(f"invalid item_id: {id_str!r}")
        item_id = int(id_str)
    except (ValueError, AttributeError) as _parse_err:
        logger.warning(f"cb_disambig parse error: {_parse_err!r}  data={cb.data!r}")
        await cb.message.edit_text("⚠️ Устаревшая кнопка. Повторите запрос.")
        return

    from app.bot.handlers.ai_handler import (
        _load_disambig, _gql, _GQL_GROUP_SCHEDULE, _GQL_LESSONS_DAY, _GQL_ROOM_SCHEDULE,
        _fmt_days_paged, _fmt_now, _make_nav_kb, _add_feedback_row,
        _store_pages, _page_key, _resolve_time, _now_moscow, TimeRef,
    )
    import json as _json

    payload = await _load_disambig(key)
    if payload is None:
        await cb.message.edit_text("⏱ Время выбора истекло. Повторите запрос.")
        return

    intent_type = payload["intent_type"]
    params      = payload["params"]
    candidates  = payload.get("candidates", [])

    # Identify the user who pressed the button
    user_tg_id = cb.from_user.id if cb.from_user else 0

    # Determine the chosen label (for storing the user's choice as a message)
    _id_field = "room_id" if intent_type == "room_schedule" else "group_id"
    chosen = next((c for c in candidates if str(c.get(_id_field, "")) == str(item_id)), None)
    chosen_label = (chosen.get("name") or str(item_id)) if chosen else str(item_id)

    # Save user's choice as a message in conversations
    asyncio.ensure_future(store_callback_choice(cb, chosen_label))

    # Remove the disambiguation keyboard
    await cb.message.edit_reply_markup(reply_markup=None)
    # Show progress
    progress = await cb.message.answer("⏳ Загружаю расписание…")

    try:
        if intent_type == "group_schedule":
            group_id  = item_id
            group_name = chosen["name"] if chosen else None
            data = await _gql(_GQL_GROUP_SCHEDULE, {
                "gn": None, "gid": group_id,
                "from": params.get("from") or _now_moscow().date().isoformat(),
                "to":   params.get("to"),
                "week": params.get("week"),
            })
            days  = data.get("groupSchedule", [])
            title = group_name or f"группа #{group_id}"
            reply = _fmt_days_paged(days, f"Расписание · {title}",
                                    show_teacher=True, show_group=False)

        elif intent_type == "group_now":
            group_id  = item_id
            group_name = chosen["name"] if chosen else None
            # Fallback: lookup name by id if not found in candidates
            if not group_name and group_id:
                from app.bot.handlers.ai_handler import _gql as _gql2, _GQL_SEARCH
                try:
                    sr = await _gql2(_GQL_SEARCH, {"q": str(group_id)})
                    hits = sr.get("search", {}).get("groups", [])
                    if hits:
                        group_name = hits[0].get("name")
                except Exception:
                    pass
            tr_raw = params.get("time_ref")
            at = _resolve_time(TimeRef(**tr_raw) if tr_raw else None)
            day = at.date().isoformat()
            data = await _gql(_GQL_LESSONS_DAY, {
                "day": day, "gid": group_id, "gn": group_name,
                "tn": None, "rn": None, "iname": None,
            })
            nodes    = data.get("lessonsOn", {}).get("nodes", [])
            at_time  = at.strftime("%H:%M")
            active   = [l for l in nodes if l["timeStart"] <= at_time <= l["timeEnd"]]
            upcoming = [l for l in nodes if l["timeStart"] > at_time]
            reply = _fmt_now(group_name or "", at_time, active, upcoming,
                             show_teacher=True, show_group=False)

        elif intent_type == "room_schedule":
            # item_id is room_id
            room_id  = item_id
            room_name = chosen["room_name"] if chosen else None
            data = await _gql(_GQL_ROOM_SCHEDULE, {
                "rn": room_name, "rid": room_id,
                "from": params.get("from") or _now_moscow().date().isoformat(),
                "to":   params.get("to"),
            })
            title = room_name or f"ауд. #{room_id}"
            days  = data.get("roomSchedule", [])
            reply = _fmt_days_paged(days, f"Расписание · {title}",
                                    show_teacher=True, show_group=True)
        else:
            reply = "❓ Неизвестный тип запроса."
    except Exception as exc:
        import secrets, string as _str
        eid = "ERR-" + "".join(secrets.choice(_str.ascii_uppercase + _str.digits) for _ in range(6))
        logger.error(f"[{eid}] disambig dispatch error: {exc}")
        try:
            from app.auth.models import AuthErrorLog
            import traceback as _tb
            await AuthErrorLog(
                level="ERROR",
                message=f"[{eid}] {type(exc).__name__}: {exc}",
                traceback=_tb.format_exc(),
                error_id=eid,
                tg_id=user_tg_id or None,
                tg_chat_id=getattr(progress, "chat", None) and progress.chat.id,
                intent=intent_type,
                details={"exc_type": type(exc).__name__},
            ).insert()
        except Exception as _le:
            logger.warning(f"error log failed: {_le}")
        await progress.edit_text(f"❌ Ошибка при загрузке расписания.\n<code>{eid}</code>", parse_mode="HTML")
        return
    _PAGED_PFX = chr(0) + "PAGED" + chr(0)
    if reply.startswith(_PAGED_PFX):
        import json as _json2
        raw = reply[len(_PAGED_PFX):]
        raw = raw[:-1] if raw.endswith(chr(0)) else raw
        try:
            pages: list[str] = _json2.loads(raw)
        except Exception:
            await progress.edit_text("❌ Ошибка обработки расписания.")
            return
        pk = _page_key(user_tg_id, raw[:40])
        await _store_pages(pk, pages)
        kb = _make_nav_kb(pk, 0, len(pages))
        kb = _add_feedback_row(kb, cb.message.chat.id, progress.message_id)
        sent = await progress.edit_text(
            pages[0] + f"\n\n<i>День 1 из {len(pages)}</i>",
            parse_mode="HTML", reply_markup=kb,
        )
        asyncio.ensure_future(store_bot_reply(sent or progress, user_tg_id))
    else:
        from app.bot.handlers.ai_handler import _split_chunks
        chunks = _split_chunks(reply)
        fb_kb = _add_feedback_row(None, cb.message.chat.id, progress.message_id)
        sent = await progress.edit_text(chunks[0] if chunks else "(пустой ответ)",
                                 parse_mode="HTML", reply_markup=fb_kb)
        asyncio.ensure_future(store_bot_reply(sent or progress, user_tg_id))
        for chunk in chunks[1:]:
            await cb.message.answer(chunk, parse_mode="HTML")



@router.callback_query(F.data.startswith("disp:"))
async def cb_disambig_page(cb: CallbackQuery) -> None:
    """
    Handle pagination in disambiguation keyboard.
    callback_data: "disp:{redis_key}:{page_idx}"
    Renders the next/prev page of group/room candidates.
    """
    await cb.answer()
    try:
        # callback_data format: "disp:{redis_key}:{page_idx}"
        # redis_key itself contains colons (e.g. "disambig:USER_ID:HASH"),
        # so we must split from the RIGHT to get the page index correctly.
        after_prefix = cb.data[5:]   # strip leading "disp:"
        key, page_str = after_prefix.rsplit(":", 1)
        page_idx = int(page_str)
    except (ValueError, IndexError, AttributeError):
        await cb.message.edit_text("⚠️ Устаревшая кнопка. Повторите запрос.")
        return

    from app.bot.handlers.ai_handler import (
        _load_disambig, _DISAMBIG_PAGE_SIZE, _store_disambig,
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    import json as _json

    payload = await _load_disambig(key)
    if payload is None:
        await cb.message.edit_text("⏱ Время выбора истекло. Повторите запрос.")
        return

    candidates  = payload["candidates"]
    intent_type = payload.get("intent_type", "group_schedule")
    total_cands = len(candidates)
    total_pages = (total_cands + _DISAMBIG_PAGE_SIZE - 1) // _DISAMBIG_PAGE_SIZE

    page_idx = max(0, min(page_idx, total_pages - 1))
    start    = page_idx * _DISAMBIG_PAGE_SIZE
    page_cands = candidates[start : start + _DISAMBIG_PAGE_SIZE]

    id_field = "room_id" if intent_type == "room_schedule" else "group_id"
    buttons = []
    for c in page_cands:
        item_id = c.get(id_field)
        if item_id is None:
            continue  # skip candidates with null IDs
        if intent_type == "room_schedule":
            label   = c["name"]
            bldg    = c.get("building", "")
            if bldg:
                label += f"  •  {bldg}"
        else:
            label   = c["name"]
            if c.get("institute_name"):
                label += f"  •  {c['institute_name']}"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"dis:{key}:{item_id}",
        )])

    # Navigation row
    nav_row = []
    if page_idx > 0:
        nav_row.append(InlineKeyboardButton(text="◀ Пред.", callback_data=f"disp:{key}:{page_idx-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page_idx+1}/{total_pages}", callback_data="pg_noop"))
    if page_idx < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="След. ▶", callback_data=f"disp:{key}:{page_idx+1}"))
    if nav_row:
        buttons.append(nav_row)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await cb.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass  # message not changed — ignore


@router.callback_query(F.data.startswith("fb:"))
async def cb_feedback(cb: CallbackQuery) -> None:
    """
    Handle 👍 / 👎 feedback buttons on bot responses.
    callback_data format: "fb:{like|dislike}:{chat_id}:{message_id}"
    - One-way: once rated, the buttons disappear from the message.
    - Idempotent: rating the same value twice is a no-op (no double-counting).
    """
    from app.auth.models import BotFeedback
    try:
        _, rating, chat_id_str, msg_id_str = cb.data.split(":", 3)
        chat_id    = int(chat_id_str)
        message_id = int(msg_id_str)
    except (ValueError, AttributeError):
        await cb.answer("⚠️ Ошибка")
        return

    user_id = cb.from_user.id if cb.from_user else 0

    try:
        doc = await BotFeedback.find_one(
            BotFeedback.chat_id    == chat_id,
            BotFeedback.message_id == message_id,
        )
        from datetime import datetime as _dt
        if doc is None:
            # First rating — try to recover user_text / bot_text from message history
            # (needed when the user rates faster than _store_feedback_meta fires)
            recovered_user_text = ""
            recovered_bot_text  = ""
            try:
                from app.models.conversation import Message as _MsgModel
                # Find the bot message (role=bot) by chat_id + message_id
                bot_msg = await _MsgModel.find_one({
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "role": "bot",
                })
                if bot_msg:
                    recovered_bot_text = bot_msg.text or bot_msg.html_text or ""
                    # Find the most recent user message that preceded this bot message
                    # (largest user message_id that is less than bot message_id)
                    user_msg = await _MsgModel.get_motor_collection().find_one(
                        {"chat_id": chat_id, "message_id": {"$lt": message_id}, "role": "user"},
                        sort=[("message_id", -1)],
                    )
                    if user_msg:
                        recovered_user_text = user_msg.get("text") or ""
            except Exception as _e:
                logger.debug(f"feedback text recovery failed: {_e}")

            # Create the record
            doc = BotFeedback(
                chat_id=chat_id,
                message_id=message_id,
                tg_id=user_id,
                user_text=recovered_user_text[:1000],
                bot_text=recovered_bot_text[:2000],
                rating=rating,
                status="rated",
                updated_at=_dt.utcnow(),
            )
            await doc.insert()
        elif doc.status == "rated" and doc.rating == rating:
            # Same rating again — no double-counting
            await cb.answer("Уже оценено ✓")
            return
        else:
            # Doc pre-created (pending) OR user changed their rating
            doc.rating     = rating
            doc.status     = "rated"
            doc.tg_id      = user_id
            doc.updated_at = _dt.utcnow()
            await doc.save()
    except Exception as exc:
        logger.warning(f"feedback save failed: {exc}")
        await cb.answer("⚠️ Не удалось сохранить оценку")
        return

    # Remove the feedback buttons from the message (they've voted)
    try:
        # Keep any existing reply_markup rows EXCEPT the feedback row
        current_kb = cb.message.reply_markup
        if current_kb:
            new_rows = [
                row for row in current_kb.inline_keyboard
                if not any(
                    btn.callback_data and btn.callback_data.startswith("fb:")
                    for btn in row
                )
            ]
            new_kb = InlineKeyboardMarkup(inline_keyboard=new_rows) if new_rows else None
        else:
            new_kb = None
        await cb.message.edit_reply_markup(reply_markup=new_kb)
    except Exception:
        pass  # message too old to edit — ignore

    icon = "👍" if rating == "like" else "👎"
    await cb.answer(f"{icon} Оценка сохранена, спасибо!")
    logger.info(f"Feedback {rating} from user {user_id} on msg {message_id} chat {chat_id}")


# ── Text messages → AI handler ─────────────────────────────────────────────────

@router.message(F.text)
async def any_text_message(message: TelegramMessage) -> None:
    # handle_message already calls store_message internally
    await handle_message(message)


# ── Media-only messages (no text / caption that would trigger AI) ──────────────
# These handlers catch every supported media type, persist the message, and
# optionally acknowledge the user.

@router.message(F.photo)
async def handle_photo(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message))
    if message.from_user:
        from app.bot.handlers.ai_handler import _upsert_user
        asyncio.ensure_future(_upsert_user(message.from_user))
    # If there's a caption treat it as a text query too
    if message.caption and message.caption.strip():
        await handle_message(message)


@router.message(F.video)
async def handle_video(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message))
    if message.caption and message.caption.strip():
        await handle_message(message)


@router.message(F.animation)
async def handle_animation(message: TelegramMessage) -> None:
    """GIF / MP4 GIF — store message and update user profile."""
    asyncio.ensure_future(store_message(message))
    if message.from_user:
        from app.bot.handlers.ai_handler import _upsert_user
        asyncio.ensure_future(_upsert_user(message.from_user))


@router.message(F.sticker)
async def handle_sticker(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message))
    if message.from_user:
        from app.bot.handlers.ai_handler import _upsert_user
        asyncio.ensure_future(_upsert_user(message.from_user))


@router.message(F.voice)
async def handle_voice(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message))


@router.message(F.video_note)
async def handle_video_note(message: TelegramMessage) -> None:
    """Rounded video — кружок."""
    asyncio.ensure_future(store_message(message))


@router.message(F.audio)
async def handle_audio(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message))
    if message.caption and message.caption.strip():
        await handle_message(message)


@router.message(F.document)
async def handle_document(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message))
    if message.caption and message.caption.strip():
        await handle_message(message)


# ── Special message types: poll, location, contact, venue ─────────────────────

@router.message(F.poll)
async def handle_poll(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message))


@router.message(F.location)
async def handle_location(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message))


@router.message(F.venue)
async def handle_venue(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message))


@router.message(F.contact)
async def handle_contact(message: TelegramMessage) -> None:
    asyncio.ensure_future(store_message(message))


# ── Command menu list (registered on startup) ──────────────────────────────────

BOT_COMMANDS = [
    BotCommand(command="start",   description="Начало работы"),
    BotCommand(command="help",    description="Справка"),
    BotCommand(command="miniapp", description="Открыть расписание (Mini App)"),
    BotCommand(command="limit",   description="Мой лимит запросов"),
    BotCommand(command="roles",   description="Мои роли и права"),
]
