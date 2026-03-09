"""
message_store.py
================
Persists every Telegram message (user → bot, bot → user) to the
"conversations" MongoDB collection via the Beanie `Conversation` model.

Key contracts
-------------
- ONE document per Telegram message (not per user).
- Media bytes are NEVER stored.  Only metadata (file_id, dimensions, …).
- Text formatting (bold/italic/links) is preserved as HTML for the dashboard.
- store_* functions are designed to be called with  asyncio.ensure_future()
  so they never block the bot response path.  All exceptions are caught and
  logged — a DB error must never crash the bot.
"""

from __future__ import annotations

import asyncio

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from aiogram.types import Message as TelegramMessage
from loguru import logger

from app.models.conversation import ForwardOrigin, MediaMeta
from app.models.conversation import Message as MessageModel
from app.models.chat_settings import ChatSettings


if TYPE_CHECKING:
    pass


# ── HTML entity converter ─────────────────────────────────────────────────────

def _esc(s: str) -> str:
    """Minimal HTML escaping via stdlib — защита от XSS/HTML-инъекций."""
    import html
    return html.escape(s)


def _entities_to_html(text: str, entities) -> str:
    """
    Convert a Telegram message text + entity list into an HTML string
    suitable for rendering in the dashboard chat viewer.
    """
    if not text:
        return ""
    if not entities:
        return _esc(text)

    parts = sorted(entities, key=lambda e: e.offset)
    result: list[str] = []
    prev = 0

    for e in parts:
        o, length = e.offset, e.length
        etype = e.type.value if hasattr(e.type, "value") else str(e.type)
        chunk = text[o: o + length]

        before = text[prev:o]
        if before:
            result.append(_esc(before))

        if etype == "bold":
            result.append(f"<b>{_esc(chunk)}</b>")
        elif etype == "italic":
            result.append(f"<i>{_esc(chunk)}</i>")
        elif etype == "underline":
            result.append(f"<u>{_esc(chunk)}</u>")
        elif etype == "strikethrough":
            result.append(f"<s>{_esc(chunk)}</s>")
        elif etype == "code":
            result.append(f"<code>{_esc(chunk)}</code>")
        elif etype == "pre":
            result.append(f"<pre>{_esc(chunk)}</pre>")
        elif etype == "spoiler":
            result.append(f'<span class="spoiler">{_esc(chunk)}</span>')
        elif etype == "text_link":
            url = getattr(e, "url", "#") or "#"
            result.append(f'<a href="{_esc(url)}" target="_blank">{_esc(chunk)}</a>')
        elif etype == "text_mention":
            uid = e.user.id if getattr(e, "user", None) else ""
            result.append(f'<a href="tg://user?id={uid}">{_esc(chunk)}</a>')
        elif etype in ("url", "email"):
            result.append(f'<a href="{_esc(chunk)}" target="_blank">{_esc(chunk)}</a>')
        elif etype == "mention":
            result.append(
                f'<a href="https://t.me/{_esc(chunk.lstrip("@"))}"'
                    f' target="_blank">{_esc(chunk)}</a>'
            )
        else:
            result.append(_esc(chunk))

        prev = o + length

    if prev < len(text):
        result.append(_esc(text[prev:]))

    return "".join(result)


def _entities_to_list(entities) -> list[dict]:
    """Serialise aiogram entity objects to plain dicts for MongoDB storage."""
    if not entities:
        return []
    out = []
    for e in entities:
        d: dict = {
            "type":   e.type.value if hasattr(e.type, "value") else str(e.type),
            "offset": e.offset,
            "length": e.length,
        }
        if getattr(e, "url", None):
            d["url"] = e.url
        if getattr(e, "user", None):
            d["user_id"]   = e.user.id
            d["user_name"] = e.user.first_name
        out.append(d)
    return out


# ── Media extraction ──────────────────────────────────────────────────────────

def _extract_media(msg: TelegramMessage) -> MediaMeta | None:
    """
    Extract media metadata from a Telegram message object.
    Returns a fully-populated MediaMeta or None for text-only messages.
    """

    # photo
    if msg.photo:
        p = max(msg.photo, key=lambda x: x.file_size or 0)
        thumb = msg.photo[0] if len(msg.photo) > 1 else None
        return MediaMeta(
            kind="photo",
            file_id=p.file_id,
            file_unique_id=p.file_unique_id,
            file_size=p.file_size,
            width=p.width,
            height=p.height,
            thumbnail_file_id=thumb.file_id if thumb else None,
        )

    # video
    if msg.video:
        v = msg.video
        return MediaMeta(
            kind="video",
            file_id=v.file_id,
            file_unique_id=v.file_unique_id,
            file_size=v.file_size,
            mime_type=v.mime_type,
            file_name=v.file_name,
            duration=v.duration,
            width=v.width,
            height=v.height,
            thumbnail_file_id=v.thumbnail.file_id if v.thumbnail else None,
        )

    # animation (GIF / MPEG4 GIF)
    if msg.animation:
        a = msg.animation
        return MediaMeta(
            kind="animation",
            file_id=a.file_id,
            file_unique_id=a.file_unique_id,
            file_size=a.file_size,
            mime_type=a.mime_type,
            file_name=a.file_name,
            duration=a.duration,
            width=a.width,
            height=a.height,
            thumbnail_file_id=a.thumbnail.file_id if a.thumbnail else None,
        )

    # sticker — static, animated (.tgs), video (.webm)
    if msg.sticker:
        s = msg.sticker
        sticker_type = (
            "animated" if s.is_animated
            else ("video" if s.is_video else "regular")
        )
        return MediaMeta(
            kind="sticker",
            file_id=s.file_id,
            file_unique_id=s.file_unique_id,
            file_size=s.file_size,
            width=s.width,
            height=s.height,
            sticker_emoji=s.emoji,
            sticker_type=sticker_type,
            sticker_set_name=s.set_name,
            thumbnail_file_id=s.thumbnail.file_id if s.thumbnail else None,
        )

    # voice
    if msg.voice:
        v = msg.voice
        return MediaMeta(
            kind="voice",
            file_id=v.file_id,
            file_unique_id=v.file_unique_id,
            file_size=v.file_size,
            mime_type=v.mime_type,
            duration=v.duration,
        )

    # video_note (rounded video — "кружок")
    if msg.video_note:
        vn = msg.video_note
        return MediaMeta(
            kind="video_note",
            file_id=vn.file_id,
            file_unique_id=vn.file_unique_id,
            file_size=vn.file_size,
            duration=vn.duration,
            # video_note has a `length` field (diameter in pixels) for both dims
            width=vn.length,
            height=vn.length,
            thumbnail_file_id=vn.thumbnail.file_id if vn.thumbnail else None,
        )

    # audio
    if msg.audio:
        a = msg.audio
        return MediaMeta(
            kind="audio",
            file_id=a.file_id,
            file_unique_id=a.file_unique_id,
            file_size=a.file_size,
            mime_type=a.mime_type,
            file_name=a.file_name,
            duration=a.duration,
            title=a.title,
            performer=a.performer,
            thumbnail_file_id=a.thumbnail.file_id if a.thumbnail else None,
        )

    # document
    if msg.document:
        d = msg.document
        return MediaMeta(
            kind="document",
            file_id=d.file_id,
            file_unique_id=d.file_unique_id,
            file_size=d.file_size,
            mime_type=d.mime_type,
            file_name=d.file_name,
            thumbnail_file_id=d.thumbnail.file_id if d.thumbnail else None,
        )

    return None

def _extract_extra(msg: TelegramMessage) -> dict | None:
    """
    Извлекает данные опросов, локации, контактов и мест (venue).
    Возвращает плоский словарь для сохранения в MongoDB.
    """
    # 1. Опросы
    if msg.poll:
        p = msg.poll
        return {
            "kind": "poll",
            "question": p.question or "",
            "options": [
                {"text": o.text, "voter_count": o.voter_count}
                for o in (p.options or [])
            ],
            "total_voter_count": p.total_voter_count,
            "is_anonymous": p.is_anonymous,
            "poll_type": str(p.type),
            "is_closed": p.is_closed,
        }

    # 2. Места (Venue)
    if msg.venue:
        v = msg.venue
        loc = v.location
        return {
            "kind": "venue",
            "latitude":  loc.latitude  if loc else None,
            "longitude": loc.longitude if loc else None,
            "title":   v.title,
            "address": v.address,
            "foursquare_id": v.foursquare_id,
            "google_place_id": v.google_place_id,
        }

    # 3. Геолокация
    if msg.location:
        loc = msg.location
        return {
            "kind": "location",
            "latitude":  loc.latitude,
            "longitude": loc.longitude,
            "horizontal_accuracy": loc.horizontal_accuracy,
            "live_period": loc.live_period,
        }

    # 4. Контакты
    if msg.contact:
        c = msg.contact
        return {
            "kind": "contact",
            "phone_number": c.phone_number,
            "first_name": c.first_name,
            "last_name":  c.last_name,
            "user_id":    c.user_id,
        }

    return None


# ── Forward info extraction ───────────────────────────────────────────────────

def _extract_forward(msg: TelegramMessage) -> ForwardOrigin | None:
    if not msg.forward_origin:
        return None

    fo = msg.forward_origin
    fo_type = type(fo).__name__

    name: str | None = None
    tg_id: int | None = None
    fwd_date: datetime | None = None

    if (u := getattr(fo, "sender_user", None)):
        name, tg_id = u.first_name, u.id

        # Если юзер скрыт, но есть имя (MessageOriginHiddenUser)
    elif (sun := getattr(fo, "sender_user_name", None)):
        name = sun

        # Если переслано из канала или чата (MessageOriginChat / Channel)
    elif (c := getattr(fo, "chat", None)):
        name = getattr(c, "title", None) or getattr(c, "username", None)
        tg_id = getattr(c, "id", None)

    if hasattr(fo, "date") and (fwd_ts := getattr(fo, "date", None)):
        fwd_date = datetime.fromtimestamp(fwd_ts.timestamp(), tz=timezone.utc)

    kind_map = {
        "MessageOriginUser":       "user",
        "MessageOriginHiddenUser": "hidden_user",
        "MessageOriginChat":       "chat",
        "MessageOriginChannel":    "channel",
    }

    return ForwardOrigin(
        kind=kind_map.get(fo_type, "unknown"),
        name=name,
        tg_id=tg_id,
        date=fwd_date,
    )


def _detect_type(msg: TelegramMessage) -> str:
    if msg.text: return "text"
    if msg.photo: return "photo"
    if msg.video: return "video"
    if msg.animation: return "animation"
    if msg.voice: return "voice"
    if msg.video_note: return "video_note"
    if msg.sticker: return "sticker"
    return "other"

    # ── Extra content extraction (poll, location, contact, venue) ────────────────


async def store_message(msg: TelegramMessage, role: str = 'user') -> None:
    """Сохранить сообщение любого типа из любого чата."""
    if not isinstance(msg, TelegramMessage):
        return

    try:
        chat = msg.chat
        user = msg.from_user or msg.sender_chat

        chat_id   = chat.id
        thread_id = getattr(msg, 'message_thread_id', None)
        chat_key  = f'{chat_id}:{thread_id or 0}'

        # Безопасное получение типа чата (str() убирает ошибку .value)
        chat_type = str(chat.type)

        message_type = _detect_type(msg)

        # Для bot-ответов в приватном чате from_user — это аккаунт бота.
        # Нам нужен tg_id пользователя (= chat.id в приватном чате),
        # чтобы bot-сообщения и user-сообщения лежали под одним ключом.
        # В группах from_user корректен — там пишут разные люди.
        if role == 'bot' and chat_type in ('private', 'ChatType.private'):
            # В приватном чате chat.id == tg_id пользователя
            effective_tg_id  = chat_id
            effective_uname  = None   # username пользователя неизвестен из bot-msg
            effective_fname  = None
            effective_lname  = None
        else:
            effective_tg_id  = getattr(user, 'id', 0)
            effective_uname  = getattr(user, 'username', None)
            effective_fname  = getattr(user, 'first_name', None)
            effective_lname  = getattr(user, 'last_name', None)

        # Используем MessageModel, чтобы линтер видел поля БД
        doc = MessageModel(
            chat_id=chat_id,
            chat_key=chat_key,
            chat_type=chat_type,
            thread_id=thread_id,
            message_id=msg.message_id,
            tg_id=effective_tg_id,
            username=effective_uname,
            first_name=effective_fname,
            last_name=effective_lname,
            role=role,
            message_type=message_type,
            # Исправляем utcfromtimestamp на современный вариант
            timestamp=msg.date.astimezone(timezone.utc),
            text=msg.text or msg.caption or '',
            html_text=_entities_to_html(
                msg.text or msg.caption or '',
                msg.entities or msg.caption_entities or []
            ),
            entities=_entities_to_list(msg.entities or msg.caption_entities or []),
            media=_extract_media(msg),
            forward=_extract_forward(msg),
            reply_to_message_id=(
                msg.reply_to_message.message_id if msg.reply_to_message else None
            ),
            reply_to_text=(
                (msg.reply_to_message.text or msg.reply_to_message.caption or '')[:200] 
                if msg.reply_to_message else None
            ),
            extra=_extract_extra(msg),
        )
        
        try:
            await doc.insert()
        except Exception as e:
            if '11000' in str(e):
                return
            raise e

        # Upsert chat-level metadata (title, username, chat_type) into ChatSettings
        # so that the dashboard can show proper names for groups/channels/private chats.
        # IMPORTANT: only pass the group/channel @username (chat.username), never the
        # user's personal @username — otherwise private chats get a "group username".
        asyncio.create_task(_upsert_chat_meta(
            chat_id=chat_id,
            chat_key=chat_key,
            chat_type=chat_type,
            title=getattr(chat, 'title', None),        # groups/channels have a title
            username=getattr(chat, 'username', None),  # group @username only, not user's
        ))
        asyncio.create_task(_enforce_limit(chat_id, chat_key))

    except Exception as exc:
        logger.warning(f'store_message failed: {exc}')

DEFAULT_LIMIT = 300

async def _upsert_chat_meta(
    chat_id: int,
    chat_key: str,
    chat_type: str,
    title: str | None,
    username: str | None,
) -> None:
    """
    Create or update the ChatSettings record for this chat with the latest
    Telegram metadata (title, username, chat_type).

    Called on every incoming message so the dashboard always has a display
    name ready — even for chats that received their first-ever message just now.
    The upsert is intentionally lightweight: it only writes when values change.
    """
    try:
        settings = await ChatSettings.find_one(ChatSettings.chat_id == chat_id)
        if settings is None:
            settings = ChatSettings(
                chat_id=chat_id,
                chat_key=chat_key,
                chat_type=chat_type,
                title=title,
                username=username,
                message_limit=DEFAULT_LIMIT,
            )
            await settings.insert()
            return

        # Only save when something actually changed to avoid unnecessary writes
        dirty = False
        if title and settings.title != title:
            settings.title = title
            dirty = True
        if username and settings.username != username:
            settings.username = username
            dirty = True
        if settings.chat_type != chat_type:
            settings.chat_type = chat_type
            dirty = True
        if dirty:
            from datetime import datetime, timezone
            settings.updated_at = datetime.now(timezone.utc)
            await settings.save()
    except Exception as exc:
        logger.warning(f'_upsert_chat_meta failed chat_id={chat_id}: {exc}')


async def _enforce_limit(chat_id: int, chat_key: str) -> None:
    try:
        settings = await ChatSettings.find_one(ChatSettings.chat_id == chat_id)

        if settings is None:
            settings = ChatSettings(
                chat_id=chat_id,
                chat_key=chat_key,
                message_limit=DEFAULT_LIMIT,
            )
            await settings.insert()

        limit = settings.message_limit
        if limit is None:
            return

        count = await MessageModel.find(MessageModel.chat_id == chat_id).count()
        excess = count - limit
        if excess <= 0:
            return

        col = MessageModel.get_pymongo_collection()


        cursor = col.find(
            {"chat_id": chat_id},
            {"_id": 1}
        ).sort([("timestamp", 1)]).limit(excess)

        ids = [doc["_id"] async for doc in cursor]

        if ids:
            await col.delete_many({"_id": {"$in": ids}})

        # 4. Обновляем время (без Deprecation Warning)
        settings.last_cleaned_at = datetime.now(timezone.utc)
        await settings.save()

    except Exception as exc:
        logger.warning(f"_enforce_limit failed chat_id={chat_id}: {exc}")


async def store_callback_choice(
    cb_query,           # aiogram CallbackQuery object
    chosen_label: str,  # human-readable button label the user tapped
    role: str = 'user',
) -> None:
    """
    Сохранить нажатие inline-кнопки как сообщение пользователя.

    CallbackQuery — это не Message, у него нет message_id своего.
    Мы записываем псевдо-сообщение с текстом выбора в ту же коллекцию,
    используя message.message_id + 1_000_000 как уникальный surrogate id,
    чтобы не конфликтовать с реальными message_id.
    """
    try:
        from app.models.conversation import Message as MessageModel
        from datetime import datetime, timezone

        chat  = cb_query.message.chat if cb_query.message else None
        user  = cb_query.from_user
        if not chat or not user:
            return

        chat_id   = chat.id
        chat_type = str(chat.type)

        # surrogate message_id: реальный id сообщения с кнопками + большой оффсет
        base_msg_id = cb_query.message.message_id if cb_query.message else 0
        surrogate_id = base_msg_id + 10_000_000

        doc = MessageModel(
            chat_id    = chat_id,
            chat_key   = f'{chat_id}:0',
            chat_type  = chat_type,
            tg_id      = user.id,
            username   = user.username,
            first_name = user.first_name,
            last_name  = user.last_name,
            message_id = surrogate_id,
            role       = role,
            message_type = 'callback_choice',
            timestamp  = datetime.now(timezone.utc),
            text       = f'[выбрал: {chosen_label}]',
            html_text  = f'[выбрал: <b>{chosen_label}</b>]',
        )
        try:
            await doc.insert()
        except Exception as e:
            if '11000' not in str(e):  # ignore duplicate key — already stored
                raise
    except Exception as exc:
        logger.warning(f'store_callback_choice failed: {exc}')


async def store_bot_reply(
    sent_message,       # aiogram Message returned from bot.send/edit
    user_tg_id: int,    # тот самый пользователь, которому отвечаем
) -> None:
    """
    Сохранить исходящее сообщение бота, явно проставив tg_id пользователя.

    Используется из callback-обработчиков, где sent_message.from_user — это
    аккаунт бота, а не пользователя. Мы передаём user_tg_id вручную.
    """
    if not sent_message:
        return
    try:
        from app.models.conversation import Message as MessageModel
        from datetime import datetime, timezone

        chat      = sent_message.chat
        chat_id   = chat.id
        chat_type = str(chat.type)

        doc = MessageModel(
            chat_id    = chat_id,
            chat_key   = f'{chat_id}:0',
            chat_type  = chat_type,
            tg_id      = user_tg_id,
            username   = None,
            first_name = None,
            last_name  = None,
            message_id = sent_message.message_id,
            role       = 'bot',
            message_type = 'text',
            timestamp  = datetime.now(timezone.utc),
            text       = sent_message.text or sent_message.caption or '',
            html_text  = sent_message.text or sent_message.caption or '',
        )
        try:
            await doc.insert()
        except Exception as e:
            if '11000' not in str(e):
                raise
    except Exception as exc:
        logger.warning(f'store_bot_reply failed: {exc}')
