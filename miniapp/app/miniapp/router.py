"""
Mini App router — all endpoints the Mini App SPA consumes.

Routes:
  GET  /miniapp          → serve index.html
  POST /miniapp/auth     → validate Telegram initData → JWT + user profile
  GET  /miniapp/api/schedule   → schedule with flexible filters
  GET  /miniapp/api/free-rooms → free rooms at a datetime
  GET  /miniapp/api/buildings  → distinct building names
  GET  /miniapp/api/search     → autocomplete (groups / teachers / rooms)
  GET  /miniapp/api/favorites  → saved favorites list
  POST /miniapp/api/favorites  → add a favorite
  DELETE /miniapp/api/favorites/{fav_id} → remove a favorite
  GET  /miniapp/api/settings   → user app settings dict
  POST /miniapp/api/settings   → merge/update settings dict
  PATCH /miniapp/api/settings  → same

NOTE: All data calls go directly to resolver functions — no HTTP self-call.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from loguru import logger
from pydantic import BaseModel

from app.auth.avatars import get_avatar_url
from app.auth.models import AuthRole, AuthUser
from app.auth.security import create_access_token, decode_access_token
from app.core.config import settings

_HERE = Path(__file__).parent / "templates"
_NO_CACHE = {"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"}

router = APIRouter(prefix="/miniapp", tags=["miniapp"])


# ── HTML shell ────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def miniapp_index():
    return HTMLResponse((_HERE / "index.html").read_text(encoding="utf-8"), headers=_NO_CACHE)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _day_to_dict(day) -> dict:
    """Convert a DayType strawberry object → plain dict for JSON response."""
    return {
        "date":        day.date,
        "weekday":     day.weekday,
        "weekdayName": day.weekday_name,
        "weekNumber":  day.week_number,
        "lessons": [_lesson_to_dict(l) for l in (day.lessons or [])],
    }


def _lesson_to_dict(l) -> dict:
    """Convert a LessonType strawberry object → plain dict."""
    return {
        "timeStart":   l.time_start,
        "timeEnd":     l.time_end,
        "subject":     l.subject,
        "lessonType":  l.lesson_type,
        "teacherName": l.teacher_name,
        "groupName":   l.group_name,
        "roomName":    l.room_name,
        "building":    l.building,
        "subgroup":    l.subgroup,
        "weekNumber":  l.week_number,
    }


async def _auth_user(authorization: Optional[str]) -> AuthUser:
    """Decode Bearer JWT → AuthUser, raise 401 on any failure."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token required")
    try:
        payload = decode_access_token(authorization[7:])
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    user = await AuthUser.get(payload["sub"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    if user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is blocked")
    return user


async def _perms(user: AuthUser) -> set[str]:
    role_docs = await AuthRole.find({"name": {"$in": user.roles}}).to_list()
    out: set[str] = set()
    for doc in role_docs:
        out.update(doc.permissions)
    return out


# ── initData auth ─────────────────────────────────────────────────────────────

class InitDataRequest(BaseModel):
    init_data: str


@router.post("/auth")
async def miniapp_auth(body: InitDataRequest):
    """
    Validate Telegram WebApp.initData and return JWT + enriched profile.
    """
    from app.auth.security import validate_telegram_init_data
    from app.auth.avatars import fetch_and_save_avatar

    tg_user = validate_telegram_init_data(body.init_data, settings.telegram_bot_token)
    if not tg_user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid initData")

    tg_id = int(tg_user["id"])

    # Upsert
    user = await AuthUser.find_one(AuthUser.tg_id == tg_id)
    if not user:
        user = AuthUser(
            tg_id=tg_id,
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name", ""),
            last_name=tg_user.get("last_name"),
        )
        await user.insert()
    else:
        user.last_active = datetime.utcnow()
        if tg_user.get("username"):
            user.username = tg_user["username"]
        await user.save()

    # Fetch avatar if missing
    if not get_avatar_url(tg_id) and settings.telegram_bot_token:
        try:
            await fetch_and_save_avatar(tg_id, settings.telegram_bot_token)
        except Exception:
            pass

    perms = await _perms(user)
    token = create_access_token(str(user.id), user.tg_id, user.roles)

    return {
        "token": token,
        "user": {
            "id":          str(user.id),
            "tg_id":       user.tg_id,
            "first_name":  user.first_name,
            "last_name":   user.last_name or "",
            "username":    user.username,
            "display":     f"{user.first_name} {user.last_name or ''}".strip(),
            "avatar":      get_avatar_url(tg_id),
            "roles":       user.roles,
            "permissions": list(perms),
            "is_blocked":  user.is_blocked,
            "is_beta":     "beta_access" in perms,
            "is_vip":      "vip_access"  in perms,
            "is_admin":    "admin:full"  in perms,
        },
    }


# ── Schedule ──────────────────────────────────────────────────────────────────

@router.get("/api/schedule")
async def schedule(
    group_name:    Optional[str] = Query(None),
    teacher_name:  Optional[str] = Query(None),
    room_name:     Optional[str] = Query(None),
    from_date:     Optional[str] = Query(None),
    to_date:       Optional[str] = Query(None),
    week:          Optional[int] = Query(None),
    # Beta post-filters (silently ignored when user has no beta_access)
    building:      Optional[str] = Query(None),
    subject:       Optional[str] = Query(None),
    lesson_type:   Optional[str] = Query(None),
    time_from:     Optional[str] = Query(None),
    time_to:       Optional[str] = Query(None),
    # VIP post-filter
    subgroup:      Optional[int] = Query(None),
    authorization: Optional[str] = Header(None),
):
    user  = await _auth_user(authorization)
    perms = await _perms(user)
    is_beta = "beta_access" in perms
    is_vip  = "vip_access"  in perms

    if not group_name and not teacher_name and not room_name:
        raise HTTPException(400, "Provide group_name, teacher_name, or room_name")

    # ── Call resolvers directly — no HTTP round-trip ──────────────────────────
    from app.graphql import resolvers as R
    try:
        if group_name:
            days_obj = await R.resolve_group_schedule(
                group_name=group_name,
                from_date=from_date, to_date=to_date, week=week,
            )
        elif teacher_name:
            days_obj = await R.resolve_teacher_schedule(
                teacher_name=teacher_name,
                from_date=from_date, to_date=to_date, week=week,
            )
        else:
            days_obj = await R.resolve_room_schedule(
                room_name=room_name,
                from_date=from_date, to_date=to_date,
            )
    except Exception as exc:
        logger.error(f"Schedule resolver failed: {exc}")
        raise HTTPException(502, f"Schedule fetch failed: {exc}")

    # Convert DayType objects → plain dicts
    days = [_day_to_dict(d) for d in days_obj]

    # Log
    from app.core.activity import log_activity
    log_activity(
        "miniapp.schedule_search",
        user_id=str(user.id), tg_id=user.tg_id,
        details={"group": group_name, "teacher": teacher_name, "room": room_name,
                 "from": from_date, "to": to_date},
    )

    # Post-filter
    def _passes(l: dict) -> bool:
        if is_beta:
            if building    and building.lower()    not in (l.get("building")    or "").lower(): return False
            if subject     and subject.lower()     not in (l.get("subject")     or "").lower(): return False
            if lesson_type and lesson_type         != l.get("lessonType"):                      return False
            if time_from   and (l.get("timeStart") or "00:00") < time_from:                    return False
            if time_to     and (l.get("timeEnd")   or "23:59") > time_to:                      return False
        if is_vip and subgroup is not None:
            if l.get("subgroup") not in (None, subgroup):                                       return False
        return True

    filtered = []
    for day in days:
        lessons = [l for l in day["lessons"] if _passes(l)]
        if lessons:
            filtered.append({**day, "lessons": lessons})

    total = sum(len(d["lessons"]) for d in filtered)
    return {"days": filtered, "meta": {"total": total, "is_beta": is_beta, "is_vip": is_vip}}


# ── Free rooms ────────────────────────────────────────────────────────────────

@router.get("/api/free-rooms")
async def free_rooms(
    at:            str,
    duration:      int           = Query(90),
    building:      Optional[str] = Query(None),
    min_capacity:  Optional[int] = Query(None),
    authorization: Optional[str] = Header(None),
):
    await _auth_user(authorization)
    from app.graphql import resolvers as R
    try:
        rooms_obj = await R.resolve_free_rooms(at=at, duration_minutes=duration, building=building)
    except Exception as exc:
        raise HTTPException(502, str(exc))

    rooms = [
        {
            "roomId":   r.room_id,
            "name":     r.name,
            "building": r.building,
            "capacity": r.capacity,
        }
        for r in rooms_obj
    ]
    if min_capacity:
        rooms = [r for r in rooms if (r.get("capacity") or 0) >= min_capacity]

    by_building: dict[str, list] = {}
    for r in rooms:
        by_building.setdefault(r.get("building") or "—", []).append(r)

    return {"rooms": rooms, "by_building": by_building, "total": len(rooms)}


# ── Buildings ─────────────────────────────────────────────────────────────────

@router.get("/api/buildings")
async def buildings(authorization: Optional[str] = Header(None)):
    await _auth_user(authorization)
    from app.graphql import resolvers as R
    try:
        result = await R.resolve_search(" ")
        bldgs = sorted({r.building for r in result.rooms if r.building})
        return {"buildings": list(bldgs)}
    except Exception:
        return {"buildings": []}


@router.get("/api/institutes-with-buildings")
async def institutes_with_buildings(authorization: Optional[str] = Header(None)):
    """
    Returns institutes list, each with their associated building names.
    Used by the free-rooms page to let users drill: institute → building → rooms.

    The Room model has no direct institute_id, but rooms belong to buildings,
    and groups belong to institutes.  We derive the mapping by looking at which
    buildings appear in rooms that are used by groups of each institute.

    Response shape:
      {
        "institutes": [
          {
            "institute_id": 1,
            "short_name": "ИМиФ",
            "name": "Институт математики и физики",
            "buildings": ["Корпус 1", "Корпус 3"]
          },
          ...
        ],
        "all_buildings": ["Корпус 1", "Корпус 2", ...]
      }
    """
    await _auth_user(authorization)
    from app.models.institute import Institute
    from app.models.group import Group
    from app.models.room import Room

    try:
        # All buildings from rooms (for the "show all" fallback option)
        all_rooms = await Room.find_all().to_list()
        all_buildings = sorted({r.building for r in all_rooms if r.building})

        institutes = await Institute.find_all().sort("short_name").to_list()

        result = []
        for inst in institutes:
            # Find all groups belonging to this institute
            groups = await Group.find({"institute_id": inst.institute_id}).to_list()
            group_ids = {g.group_id for g in groups}

            if not group_ids:
                result.append({
                    "institute_id": inst.institute_id,
                    "short_name":   inst.short_name,
                    "name":         inst.name,
                    "buildings":    [],
                })
                continue

            # Используем Room.institute_ids напрямую (добавлено в модель).
            # Фоллбек через group_ids если institute_ids ещё не проставлены (до миграции).
            rooms_for_inst = await Room.find(
                {"institute_ids": inst.institute_id, "building": {"$ne": None}}
            ).to_list()
            if not rooms_for_inst:
                # Фоллбек: через group_ids (старые данные до миграции)
                rooms_for_inst = await Room.find(
                    {"group_ids": {"$in": list(group_ids)}, "building": {"$ne": None}}
                ).to_list()
            buildings_for_inst = sorted({r.building for r in rooms_for_inst if r.building})

            result.append({
                "institute_id": inst.institute_id,
                "short_name":   inst.short_name,
                "name":         inst.name,
                "buildings":    buildings_for_inst,
            })

        # Sort: institutes with buildings first, then alphabetically
        result.sort(key=lambda x: (len(x["buildings"]) == 0, x["short_name"]))

        return {"institutes": result, "all_buildings": all_buildings}

    except Exception as exc:
        from loguru import logger
        logger.warning(f"institutes_with_buildings failed: {exc}")
        return {"institutes": [], "all_buildings": []}


# ── Search (autocomplete) ─────────────────────────────────────────────────────

@router.get("/api/search")
async def search(
    q:             str,
    authorization: Optional[str] = Header(None),
):
    await _auth_user(authorization)
    if len(q.strip()) < 2:
        return {"groups": [], "teachers": [], "rooms": []}

    from app.graphql import resolvers as R
    try:
        result = await R.resolve_search(q)
        return {
            "groups": [
                {"groupId": g.group_id, "name": g.name,
                 "instituteName": g.institute_name, "course": g.course}
                for g in result.groups
            ],
            "teachers": [
                {"teacherId": t.teacher_id, "fullName": t.full_name, "shortName": t.short_name}
                for t in result.teachers
            ],
            "rooms": [
                {"roomId": r.room_id, "name": r.name, "building": r.building}
                for r in result.rooms
            ],
        }
    except Exception as exc:
        raise HTTPException(502, str(exc))


# ── Favorites ─────────────────────────────────────────────────────────────────

class FavoriteBody(BaseModel):
    type:  str   # "group" | "teacher" | "room"
    id:    str   # entity name / identifier used for lookups
    label: str   # human display label


@router.get("/api/favorites")
async def get_favorites(authorization: Optional[str] = Header(None)):
    user = await _auth_user(authorization)
    return {"favorites": user.miniapp_favorites or []}


@router.post("/api/favorites")
async def add_favorite(
    body: FavoriteBody,
    authorization: Optional[str] = Header(None),
):
    user = await _auth_user(authorization)
    favs: list[dict] = list(user.miniapp_favorites or [])
    if not any(f["type"] == body.type and f["id"] == body.id for f in favs):
        favs.append({"type": body.type, "id": body.id, "label": body.label})
    favs = favs[:50]
    user.miniapp_favorites = favs
    await user.save()
    return {"favorites": favs}


@router.delete("/api/favorites/{fav_id}")
async def remove_favorite(
    fav_id: str,
    authorization: Optional[str] = Header(None),
):
    """fav_id = '<type>:<id>' e.g. 'group:ИСС-б-о-22-3'"""
    user = await _auth_user(authorization)
    favs = [
        f for f in (user.miniapp_favorites or [])
        if f"{f['type']}:{f['id']}" != fav_id
    ]
    user.miniapp_favorites = favs
    await user.save()
    return {"favorites": favs}


# ── Settings ──────────────────────────────────────────────────────────────────

class SettingsBody(BaseModel):
    weekFromMonday:  Optional[bool] = None
    time24h:         Optional[bool] = None
    compact:         Optional[bool] = None
    notifications:   Optional[bool] = None
    default_group:   Optional[str]  = None
    default_teacher: Optional[str]  = None
    theme:           Optional[str]  = None
    accent_color:    Optional[str]  = None   # hex color e.g. "#7c6eff"


@router.get("/api/settings")
async def get_settings(authorization: Optional[str] = Header(None)):
    user = await _auth_user(authorization)
    return {"settings": user.miniapp_settings or {}}


async def _do_update_settings(body: SettingsBody, authorization: Optional[str]) -> dict:
    user = await _auth_user(authorization)
    s = dict(user.miniapp_settings or {})
    for k, v in body.model_dump(exclude_none=True).items():
        s[k] = v
    user.miniapp_settings = s
    # Also persist accent_color on the user document itself for dashboard injection
    if body.accent_color:
        user.accent_color = body.accent_color
    await user.save()
    return {"settings": s}


@router.post("/api/settings")
async def update_settings_post(body: SettingsBody, authorization: Optional[str] = Header(None)):
    return await _do_update_settings(body, authorization)


@router.patch("/api/settings")
async def update_settings_patch(body: SettingsBody, authorization: Optional[str] = Header(None)):
    return await _do_update_settings(body, authorization)


@router.get("/api/profile/limits")
async def profile_limits(authorization: Optional[str] = Header(None)):
    """
    Return the current user's AI-query quota status.
    Used by the miniapp profile tab to display usage.
    """
    user = await _auth_user(authorization)

    from app.miniapp.quota_service import get_quota_status
    status = await get_quota_status(
        user_id=user.tg_id,
        chat_id=user.tg_id,
        chat_type="private",
    )
    return status


# ── Support ticket ────────────────────────────────────────────────────────────

class SupportBody(BaseModel):
    message:  str
    category: str = "other"   # bug | suggestion | question | other


@router.post("/api/support")
async def submit_support(body: SupportBody, authorization: Optional[str] = Header(None)):
    """Submit a support ticket from the Mini App."""
    user = await _auth_user(authorization)
    if not body.message.strip():
        from fastapi import HTTPException
        raise HTTPException(400, "Empty message")

    from app.auth.models import SupportTicket
    valid_cats = {"bug", "suggestion", "question", "other"}
    category   = body.category if body.category in valid_cats else "other"
    ticket = SupportTicket(
        tg_id=user.tg_id,
        username=user.username or "",
        first_name=user.first_name or "",
        message=body.message.strip(),
        status="open",
        source="miniapp",
        category=category,
    )
    await ticket.insert()

    # Notify admin via support bot
    from app.core.config import settings
    if settings.support_bot_token and settings.support_admin_chat_id:
        import httpx
        try:
            name = f"{user.first_name or ''} @{user.username or user.tg_id}".strip()
            async with httpx.AsyncClient(timeout=8) as client:
                await client.post(
                    f"https://api.telegram.org/bot{settings.support_bot_token}/sendMessage",
                    json={
                        "chat_id": settings.support_admin_chat_id,
                        "text": (
                            f"📬 <b>Новый тикет из MiniApp</b>\n"
                                f"От: {name} (tg_id={user.tg_id})\n"
                                f"ID: <code>{str(ticket.id)}</code>\n\n"
                                f"{body.message[:500]}\n\n"
                                f"Ответить:\n"
                                f"<code>/reply {str(ticket.id)} Ваш ответ здесь</code>"
                        ),
                        "parse_mode": "HTML",
                    },
                )
        except Exception as exc:
            from loguru import logger
            logger.warning(f"miniapp support notify failed: {exc}")

    return {"ok": True, "ticket_id": str(ticket.id)}
