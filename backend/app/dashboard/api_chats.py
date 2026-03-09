from fastapi import APIRouter, Depends, Query
from datetime import datetime, timezone
from app.models.conversation import Message
from app.models.chat_settings import ChatSettings
from typing import Optional
from app.auth.dependencies import require_admin
from pydantic import BaseModel
from app.dashboard.message_utils import _enforce_limit
import asyncio

router = APIRouter(prefix='/dashboard/api', tags=['dashboard-chats'])


@router.get('/chats')
async def list_chats(
    type: Optional[str] = Query(None),  # private|group|supergroup|channel
    _=Depends(require_admin),
):
    pipeline = [
        # ── BUG 1 FIX: filter out documents where chat_id is null ──────────────
        # Old messages written before the chat_id field was added to the schema
        # (e.g. migrated from the legacy ChatMessage model) have chat_id=null in
        # MongoDB.  $group then produces a single bucket with _id=null, which the
        # frontend renders as "chat:null" and tries to open as /chats/null — which
        # FastAPI rejects because the path param is typed as `int`.
        # Solution: drop null-chat_id documents before grouping.
        {'$match': {'chat_id': {'$ne': None}}},

        {'$group': {
            '_id':        '$chat_id',
            'chat_type':  {'$first': '$chat_type'},
            'last_msg':   {'$max':   '$timestamp'},
            'msg_count':  {'$sum':   1},
            'last_user':  {'$last':  '$first_name'},
            'last_text':  {'$last':  '$text'},

            # ── BUG 2 FIX: collect display info for private chats ───────────────
            # Private chats have no title in ChatSettings (it's never set because
            # Telegram private chats don't have a group name).  The frontend falls
            # back to `chat: ${chat_id}` which looks ugly for actual users.
            # We pull first_name / last_name / username directly from the messages
            # so we can build a proper display name for private chats server-side.
            'user_first': {'$first': '$first_name'},
            'user_last':  {'$first': '$last_name'},
            'user_uname': {'$first': '$username'},
            'tg_id':      {'$first': '$tg_id'},
        }},
        {'$sort': {'last_msg': -1}},
    ]

    # Type filter is inserted before $match so it runs on raw documents
    if type:
        pipeline.insert(0, {'$match': {'chat_type': type}})

    col = Message.get_pymongo_collection()
    chats = [doc async for doc in col.aggregate(pipeline)]

    # Enrich with ChatSettings (title, limit, logging flag)
    chat_ids = [c['_id'] for c in chats]
    settings_list = await ChatSettings.find(
        {'chat_id': {'$in': chat_ids}}
    ).to_list()
    settings_map = {s.chat_id: s for s in settings_list}

    result = []
    for c in chats:
        cid = c['_id']
        s   = settings_map.get(cid)

        # ── BUG 2 FIX (continued): build display name ──────────────────────────
        # Priority: ChatSettings.title (set for groups/channels) →
        #           first_name + last_name from messages (private chats) →
        #           @username → tg:{tg_id}
        chat_type = c.get('chat_type', 'private')
        if s and s.title:
            display_title = s.title
        elif chat_type == 'private':
            parts = [c.get('user_first'), c.get('user_last')]
            name  = ' '.join(p for p in parts if p).strip()
            display_title = name or (
                f"@{c['user_uname']}" if c.get('user_uname') else f"tg:{c.get('tg_id', cid)}"
            )
        else:
            # group/supergroup/channel without a ChatSettings record yet
            display_title = f"chat:{cid}"

        result.append({
            'chat_id':            cid,
            'chat_type':          chat_type,
            'title':              display_title,
            'username':           s.username if s else c.get('user_uname'),
            'tg_id':              c.get('tg_id'),
            'last_msg':           c.get('last_msg'),
            'msg_count':          c.get('msg_count'),
            'last_user':          c.get('last_user'),
            'last_text':          (c.get('last_text') or '')[:80],
            'message_limit':      s.message_limit if s else 300,
            'logging_enabled':    s.logging_enabled if s else True,
            # Bot AI-query quota — None means "use global defaults"
            'bot_quota_cap':      s.bot_quota_cap if s else None,
            'bot_quota_ttl_hours': s.bot_quota_ttl_hours if s else None,
        })
    return result


@router.get('/chats/{chat_id}/threads')
async def get_threads(
    chat_id: int,
    _=Depends(require_admin),
):
    """Return distinct thread_ids for a supergroup chat."""
    col = Message.get_pymongo_collection()
    pipeline = [
        {'$match': {'chat_id': chat_id, 'thread_id': {'$ne': None}}},
        {'$group': {
            '_id':       '$thread_id',
            'msg_count': {'$sum': 1},
            'last_msg':  {'$max': '$timestamp'},
        }},
        {'$sort': {'last_msg': -1}},
    ]
    threads = [doc async for doc in col.aggregate(pipeline)]
    return [
        {'thread_id': t['_id'], 'title': f'Тема {t["_id"]}', 'msg_count': t['msg_count']}
        for t in threads
    ]


@router.get('/chats/{chat_id}/messages')
async def get_messages(
    chat_id:   int,
    limit:     int               = Query(50, le=200),
    offset:    int               = Query(0),
    thread_id: Optional[int]     = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date:   Optional[datetime] = Query(None),
    msg_type:  Optional[str]     = Query(None),
    search:    Optional[str]     = Query(None),
    _=Depends(require_admin),
):
    # Use raw PyMongo dict query to avoid Beanie operator &= TypeError
    # (Beanie Eq/GTE objects can't be combined with bitwise-and once mixed).
    import re as _re
    query: dict = {'chat_id': chat_id}
    if thread_id is not None:
        query['thread_id'] = thread_id
    if from_date and to_date:
        query['timestamp'] = {'$gte': from_date, '$lte': to_date}
    elif from_date:
        query['timestamp'] = {'$gte': from_date}
    elif to_date:
        query['timestamp'] = {'$lte': to_date}
    if msg_type:
        query['message_type'] = msg_type
    if search:
        query['text'] = {'$regex': _re.escape(search), '$options': 'i'}

    col   = Message.get_pymongo_collection()
    total = await col.count_documents(query)
    docs  = await col.find(query).sort('timestamp', -1).skip(offset).limit(limit).to_list(limit)

    items = []
    for raw in docs:
        raw['id'] = str(raw.pop('_id', ''))
        try:
            m = Message.model_validate(raw)
        except Exception:
            continue
        d = m.model_dump()
        if m.media:
            d['media_type']     = m.media.kind
            d['file_id']        = m.media.file_id
            d['file_unique_id'] = m.media.file_unique_id
            d['file_size']      = m.media.file_size
            d['width']          = m.media.width
            d['height']         = m.media.height
            d['duration']       = m.media.duration
            d['file_name']      = m.media.file_name
            d['title']          = m.media.title
            d['mime_type']      = m.media.mime_type
            d['sticker_emoji']  = m.media.sticker_emoji
            d['media_url']      = None   # resolved client-side via proxy
        items.append(d)

    return {'total': total, 'items': items, 'offset': offset, 'limit': limit}


class ChatSettingsUpdate(BaseModel):
    message_limit:        Optional[int] = None
    time_limit_days:      Optional[int] = None
    logging_enabled:      bool          = True
    # Bot AI-query quota overrides (None = revert to global defaults)
    bot_quota_cap:        Optional[int] = None
    bot_quota_ttl_hours:  Optional[int] = None


@router.patch('/chats/{chat_id}/settings')
async def update_settings(
    chat_id: int,
    body:    ChatSettingsUpdate,
    _=Depends(require_admin),
):
    settings = await ChatSettings.find_one(ChatSettings.chat_id == chat_id)
    if settings is None:
        settings = ChatSettings(chat_id=chat_id, chat_key=f'{chat_id}:0')
        await settings.insert()

    settings.message_limit       = body.message_limit
    settings.time_limit_days     = body.time_limit_days
    settings.logging_enabled     = body.logging_enabled
    settings.bot_quota_cap       = body.bot_quota_cap
    settings.bot_quota_ttl_hours = body.bot_quota_ttl_hours
    settings.updated_at          = datetime.now(timezone.utc)
    await settings.save()

    if body.message_limit is not None:
        asyncio.ensure_future(_enforce_limit(chat_id, f'{chat_id}:0'))

    return {
        'ok':                  True,
        'chat_id':             chat_id,
        'message_limit':       settings.message_limit,
        'bot_quota_cap':       settings.bot_quota_cap,
        'bot_quota_ttl_hours': settings.bot_quota_ttl_hours,
    }


# ── Bot Feedback endpoints ────────────────────────────────────────────────────

from app.auth.models import BotFeedback


@router.get('/feedback')
async def list_feedback(
    rating:  Optional[str] = Query(None),   # like | dislike
    status:  Optional[str] = Query(None),   # pending | rated
    limit:   int            = Query(50, le=200),
    offset:  int            = Query(0),
    _=Depends(require_admin),
):
    """Return paginated bot feedback, optionally filtered by rating and/or status."""
    query: dict = {}
    if rating in ('like', 'dislike'):
        query['rating'] = rating
    if status in ('pending', 'rated'):
        query['status'] = status

    col   = BotFeedback.get_pymongo_collection()
    total = await col.count_documents(query)
    docs  = await col.find(query).sort('created_at', -1).skip(offset).limit(limit).to_list(limit)

    items = []
    for d in docs:
        d['id'] = str(d.pop('_id', ''))
        items.append(d)

    return {'total': total, 'items': items, 'offset': offset, 'limit': limit}


@router.get('/feedback/stats')
async def feedback_stats(_=Depends(require_admin)):
    col = BotFeedback.get_pymongo_collection()
    likes    = await col.count_documents({'rating': 'like'})
    dislikes = await col.count_documents({'rating': 'dislike'})
    total    = likes + dislikes
    return {
        'likes':    likes,
        'dislikes': dislikes,
        'total':    total,
        'pct_like': round(likes / total * 100) if total else 0,
    }
