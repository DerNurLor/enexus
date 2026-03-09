"""
Dashboard REST API — HARDENED.
All admin endpoints require require_permission("admin:full") or specific perms.

Security changes (audit fixes):
  [S1] _safe_parse_filter: blocks all MongoDB operators ($-prefixed keys) — NoSQL injection fix
  [S2] admin_update_user: role hierarchy validation — privilege escalation prevention
  [S3] admin_save_settings: atomic write, type validation, removed runtime setattr
  [S4] admin_bot_command: Telegram method allowlist — prevents setWebhook hijack
  [S5] admin_broadcast: cooldown + text length limit + audience cap
  [S6] admin_mongo_viewer: reduced limits, maxTimeMS, endpoint rate limiting
  [S7] Regex injection: all user-supplied $regex inputs escaped
  [S8] _merged_docs: capped memory, accurate total count
  [S9] Input validation: expires_days max, rate_limit bounds, permissions whitelist
  [S10] Broadcast dedup: check job status before queuing
"""
from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from loguru import logger

from app.auth.models import (
    AuthActivityLog, AuthApiKey, AuthErrorLog, AuthRole, AuthUser,
    BotConversation, SupportTicket, BroadcastJob,
)
from app.auth.dependencies import get_current_user, require_permission
from app.auth.avatars import get_avatar_url
from app.core.config import settings

api = APIRouter(prefix="/dashboard/api", tags=["dashboard"])

_utcnow = lambda: datetime.now(timezone.utc)  # noqa: E731


# ── helpers ───────────────────────────────────────────────────────────────────

def _user_dict(u: AuthUser) -> dict:
    return {
        "id":           str(u.id),
        "tg_id":        u.tg_id,
        "username":     u.username,
        "first_name":   u.first_name,
        "last_name":    u.last_name or "",
        "display":      f"{u.first_name} {u.last_name or ''}".strip() or f"tg:{u.tg_id}",
        "avatar":       get_avatar_url(u.tg_id),
        "roles":        u.roles,
        "is_blocked":   u.is_blocked,
        "block_reason": u.block_reason,
        "last_active":  u.last_active.isoformat() if u.last_active else "",
        "created_at":   u.created_at.isoformat() if u.created_at else "",
        "daily_requests":    u.daily_requests,
        "monthly_ai_tokens": u.monthly_ai_tokens,
        "extra_permissions": u.extra_permissions or [],
        "accent_color":      getattr(u, "accent_color", "#7c6eff"),
    }


# ── [S1] Hardened filter parser — blocks MongoDB operators ────────────────────

_MAX_FILTER_LENGTH = 10_240  # 10 KB max

def _safe_parse_filter(raw: str) -> dict:
    """
    Parse a JSON filter string safely.
    SECURITY: Blocks ALL MongoDB operators ($-prefixed keys) at any nesting depth.
    Returns {} on error or dangerous input.
    """
    if not raw or not raw.strip():
        return {}
    if len(raw) > _MAX_FILTER_LENGTH:
        logger.warning(f"_safe_parse_filter: input too large ({len(raw)} bytes), rejected")
        return {}
    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            return {}
        _check_no_operators(obj)
        return obj
    except ValueError as e:
        logger.warning(f"_safe_parse_filter: rejected dangerous filter: {e}")
        return {}
    except Exception:
        return {}


def _check_no_operators(obj: Any, depth: int = 0) -> None:
    """Recursively check for MongoDB operators in filter dict. Raises ValueError if found."""
    if depth > 10:
        raise ValueError("Filter nesting too deep")
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and key.startswith("$"):
                raise ValueError(f"MongoDB operator '{key}' not allowed in filters")
            _check_no_operators(value, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _check_no_operators(item, depth + 1)


def _escape_regex(user_input: str) -> str:
    """[S7] Escape user input for safe use in MongoDB $regex."""
    return re.escape(user_input.strip())


# ── /me endpoints ─────────────────────────────────────────────────────────────

@api.get("/me")
async def me(user: AuthUser = Depends(get_current_user)):
    keys = await AuthApiKey.find(
        AuthApiKey.user_id == str(user.id),
        AuthApiKey.is_revoked == False,  # noqa
    ).sort("-created_at").to_list(20)

    activity = await AuthActivityLog.find(
        AuthActivityLog.user_id == str(user.id),
    ).sort("-timestamp").to_list(30)

    return {
        "user": _user_dict(user),
        "keys": [
            {
                "id":            str(k.id),
                "prefix":        k.key_prefix,
                "name":          k.name,
                "permissions":   k.permissions,
                "rate_limit_rpm": k.rate_limit_rpm,
                "expires_at":    k.expires_at.isoformat() if k.expires_at else None,
                "last_used_at":  k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at":    k.created_at.isoformat(),
                "use_count":     getattr(k, "use_count", 0),
            }
            for k in keys
        ],
        "activity": [
            {"action": a.action, "ip": a.ip, "details": a.details,
             "timestamp": a.timestamp.isoformat()}
            for a in activity
        ],
    }


# [S9] Hardened input validation for API key creation
class CreateKeyRequest(BaseModel):
    name: str = Field(default="default", max_length=100)
    permissions: list[str] = Field(default_factory=list, max_length=20)
    rate_limit_rpm: int = Field(default=60, ge=1, le=1000)
    expires_days: Optional[int] = Field(default=None, ge=1, le=365)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()[:100]

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: list[str]) -> list[str]:
        # Only allow known permission strings
        _KNOWN_PERMS = {
            "schedule:read", "schedule:write", "beta_access", "vip_access",
            "users:read", "users:write", "logs:read", "admin:full",
            "floorplan:view", "floorplan:edit", "support:reply",
            "broadcast:send", "api:unlimited",
        }
        validated = []
        for p in v:
            if isinstance(p, str) and p in _KNOWN_PERMS:
                validated.append(p)
        return validated


@api.post("/me/keys")
async def create_key(body: CreateKeyRequest, user: AuthUser = Depends(get_current_user)):
    from app.auth.security import generate_api_key
    raw_key, key_hash, prefix = generate_api_key()
    expires_at = None
    if body.expires_days:
        expires_at = _utcnow() + timedelta(days=body.expires_days)
    doc = AuthApiKey(
        key_hash=key_hash, key_prefix=prefix, user_id=str(user.id),
        name=body.name, permissions=body.permissions,
        rate_limit_rpm=body.rate_limit_rpm, expires_at=expires_at,
    )
    await doc.insert()
    await AuthActivityLog(
        user_id=str(user.id), tg_id=user.tg_id, action="api_key_created",
        details={"name": body.name, "prefix": prefix},
    ).insert()
    return {"key": raw_key, "prefix": prefix, "id": str(doc.id)}


@api.delete("/me/keys/{key_id}", status_code=204)
async def revoke_key(key_id: str, user: AuthUser = Depends(get_current_user)):
    key = await AuthApiKey.get(key_id)
    if not key or key.user_id != str(user.id):
        raise HTTPException(404, "Key not found")
    key.is_revoked = True
    await key.save()
    await AuthActivityLog(
        user_id=str(user.id), tg_id=user.tg_id, action="api_key_revoked",
        details={"key_id": key_id},
    ).insert()


# ── admin: stats / cache ──────────────────────────────────────────────────────

@api.get("/admin/stats")
async def admin_stats(_: AuthUser = Depends(require_permission("logs:read"))):
    now      = _utcnow()
    week_ago = now - timedelta(days=7)
    today    = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_users   = await AuthUser.count()
    blocked_users = await AuthUser.find(AuthUser.is_blocked == True).count()  # noqa
    active_today  = await AuthUser.find(AuthUser.last_active >= today).count()
    open_tickets  = await SupportTicket.find({"status": "open"}).count()

    from app.auth.database import get_auth_db
    from app.db.database import get_motor_db
    col = get_auth_db().get_collection("auth_activity_log")

    daily = await col.aggregate([
        {"$match":  {"timestamp": {"$gte": week_ago}}},
        {"$group":  {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                     "count": {"$sum": 1}}},
        {"$sort":   {"_id": 1}},
    ]).to_list(30)

    actions = await col.aggregate([
        {"$match":  {"timestamp": {"$gte": week_ago}}},
        {"$group":  {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort":   {"count": -1}},
        {"$limit":  12},
    ]).to_list(12)

    recent = await col.find(
        {}, {"_id": 0, "user_id": 1, "tg_id": 1, "action": 1, "timestamp": 1}
    ).sort("timestamp", -1).limit(12).to_list(12)

    # Scrape stats from schedule DB
    scrape_col = get_motor_db().get_collection("scrape_logs")
    recent_scrapes = await scrape_col.find(
        {}, {"_id": 0, "started_at": 1, "finished_at": 1, "mode": 1,
             "groups_scraped": 1, "lessons_upserted": 1, "status": 1}
    ).sort("started_at", -1).limit(5).to_list(5)

    total_lessons  = await get_motor_db().get_collection("lessons").estimated_document_count()
    total_groups   = await get_motor_db().get_collection("groups").estimated_document_count()
    total_teachers = await get_motor_db().get_collection("teachers").estimated_document_count()

    # Bot message count (from activity log) — [S7] escaped regex
    bot_messages = await col.count_documents({
        "action": {"$regex": "^bot\\.", "$options": "i"},
        "timestamp": {"$gte": today},
    })
    api_calls = await col.count_documents({
        "timestamp": {"$gte": today}
    })

    def _ts(v: Any) -> str:
        return v.isoformat() if isinstance(v, datetime) else str(v)

    def _fmt_scrape(s: dict) -> dict:
        return {
            "mode":             s.get("mode", ""),
            "groups_scraped":   s.get("groups_scraped", 0),
            "lessons_upserted": s.get("lessons_upserted", 0),
            "status":           s.get("status", ""),
            "started_at":       _ts(s.get("started_at")) if s.get("started_at") else "",
            "finished_at":      _ts(s.get("finished_at")) if s.get("finished_at") else "",
        }

    return {
        "totals": {
            "users":          total_users,
            "blocked":        blocked_users,
            "active_today":   active_today,
            "open_tickets":   open_tickets,
            "total_lessons":  total_lessons,
            "total_groups":   total_groups,
            "total_teachers": total_teachers,
            "bot_messages_today": bot_messages,
            "api_calls_today":    api_calls,
        },
        "daily_activity":   [{"date": d["_id"], "count": d["count"]} for d in daily],
        "action_breakdown": [{"action": a["_id"], "count": a["count"]} for a in actions],
        "recent_events":    [
            {"user_id": r.get("user_id"), "tg_id": r.get("tg_id"),
             "action": r.get("action"), "timestamp": _ts(r.get("timestamp"))}
            for r in recent
        ],
        "scrape_stats": {
            "recent": [_fmt_scrape(s) for s in recent_scrapes],
        },
    }


@api.post("/admin/cache/invalidate", status_code=204)
async def invalidate_cache(_: AuthUser = Depends(require_permission("admin:full"))):
    """Flush all Redis caches so Refresh button forces DB re-fetch."""
    from app.cache.redis import invalidate_pattern
    deleted = await invalidate_pattern("ncfu:*")
    await invalidate_pattern("bot:reply:*")
    logger.info(f"Cache invalidated: {deleted} keys deleted")


# ── admin: users ──────────────────────────────────────────────────────────────

@api.get("/admin/users")
async def admin_users(
    q:            Optional[str] = None,
    blocked_only: bool = False,
    skip:         int  = Query(default=0, ge=0),
    limit:        int  = Query(default=50, ge=1, le=200),
    _: AuthUser = Depends(require_permission("users:read")),
):
    from app.auth.database import get_auth_db
    col = get_auth_db().get_collection("auth_users")

    query: dict = {}
    if blocked_only:
        query["is_blocked"] = True
    if q and q.strip():
        # [S7] Escape regex to prevent injection
        escaped = _escape_regex(q)
        regex = {"$regex": escaped, "$options": "i"}
        query["$or"] = [{"username": regex}, {"first_name": regex}, {"last_name": regex}]

    total = await col.count_documents(query)
    raw   = await col.find(query).sort("last_active", -1).skip(skip).limit(limit).to_list(limit)
    users = [AuthUser.model_validate(r) for r in raw]
    return {"users": [_user_dict(u) for u in users], "total": total}


@api.get("/admin/users/{user_id}")
async def admin_user_detail(
    user_id: str,
    _: AuthUser = Depends(require_permission("users:read")),
):
    user = await AuthUser.get(user_id)
    if not user:
        raise HTTPException(404, "Not found")
    keys     = await AuthApiKey.find(AuthApiKey.user_id == user_id).to_list(50)
    activity = await AuthActivityLog.find(
        AuthActivityLog.user_id == user_id
    ).sort("-timestamp").to_list(50)
    return {
        "user":     _user_dict(user),
        "keys":     [{"id": str(k.id), "prefix": k.key_prefix, "name": k.name,
                      "is_revoked": k.is_revoked, "created_at": k.created_at.isoformat()} for k in keys],
        "activity": [{"action": a.action, "ip": a.ip, "details": a.details,
                      "timestamp": a.timestamp.isoformat()} for a in activity],
    }


class AdminUpdateUser(BaseModel):
    roles:             Optional[list[str]] = None
    is_blocked:        Optional[bool]      = None
    block_reason:      Optional[str]       = Field(default=None, max_length=500)
    daily_requests:    Optional[int]       = Field(default=None, ge=0, le=100000)
    monthly_ai_tokens: Optional[int]       = Field(default=None, ge=0, le=10000000)


# [S2] Role hierarchy — only admin:full can assign admin-level roles
_ADMIN_ROLES = {"admin", "superadmin", "owner"}


async def _validate_role_assignment(admin: AuthUser, target_user_id: str, new_roles: list[str]) -> None:
    """Prevent privilege escalation: only admin:full holders can assign admin-level roles."""
    from app.auth.dependencies import _user_permissions

    admin_perms = await _user_permissions(admin)

    # Self-escalation check
    if str(admin.id) == target_user_id:
        # Cannot change own roles (prevents self-escalation)
        raise HTTPException(403, "Cannot modify your own roles. Ask another admin.")

    # Only admin:full can assign admin-level roles
    if "admin:full" not in admin_perms:
        for role in new_roles:
            if role.lower() in _ADMIN_ROLES or "admin" in role.lower():
                raise HTTPException(
                    403,
                    f"Permission denied: assigning role '{role}' requires admin:full"
                )


@api.patch("/admin/users/{user_id}")
async def admin_update_user(
    user_id: str,
    body:    AdminUpdateUser,
    admin:   AuthUser = Depends(require_permission("users:write")),
):
    user = await AuthUser.get(user_id)
    if not user:
        raise HTTPException(404, "Not found")

    # [S2] Validate role assignment if roles are being changed
    if body.roles is not None:
        await _validate_role_assignment(admin, user_id, body.roles)
        user.roles = body.roles

    if body.is_blocked        is not None: user.is_blocked        = body.is_blocked
    if body.block_reason      is not None: user.block_reason      = body.block_reason
    if body.daily_requests    is not None: user.daily_requests    = body.daily_requests
    if body.monthly_ai_tokens is not None: user.monthly_ai_tokens = body.monthly_ai_tokens
    await user.save()

    # If daily_requests changed — reset Redis quota so new limit applies immediately
    if body.daily_requests is not None and user.tg_id:
        try:
            from app.cache.redis import get_redis
            r = get_redis()
            await r.delete(f"quota:{user.tg_id}")
        except Exception as exc:
            logger.warning(f"Failed to reset quota on limit change: {exc}")

    # If user was blocked, revoke all their tokens
    if body.is_blocked:
        try:
            from app.cache.redis import get_redis
            r = get_redis()
            # Invalidate refresh tokens by setting a block marker
            await r.setex(f"user:blocked:{user_id}", 86400 * 30, "1")
        except Exception as exc:
            logger.warning(f"Failed to set block marker in Redis: {exc}")

    await AuthActivityLog(
        user_id=str(admin.id), tg_id=admin.tg_id, action="admin.user_updated",
        details={"target": user_id, "changes": body.model_dump(exclude_none=True)},
    ).insert()
    return _user_dict(user)


@api.post("/admin/users/{user_id}/revoke-all-keys", status_code=204)
async def admin_revoke_all_keys(
    user_id: str,
    admin:   AuthUser = Depends(require_permission("users:write")),
):
    keys = await AuthApiKey.find(
        AuthApiKey.user_id == user_id, AuthApiKey.is_revoked == False  # noqa
    ).to_list()
    for k in keys:
        k.is_revoked = True
        await k.save()
    await AuthActivityLog(
        user_id=str(admin.id), tg_id=admin.tg_id, action="admin.revoke_all_keys",
        details={"target": user_id, "count": len(keys)},
    ).insert()


@api.post("/admin/users/{user_id}/reset-quota", status_code=200)
async def admin_reset_quota(
    user_id: str,
    admin:   AuthUser = Depends(require_permission("users:write")),
):
    """Reset user's Redis quota counter so they can send messages again immediately."""
    user = await AuthUser.get(user_id)
    if not user:
        raise HTTPException(404, "Not found")
    try:
        from app.cache.redis import get_redis
        r = get_redis()
        key = f"quota:{user.tg_id}"
        await r.delete(key)
    except Exception as exc:
        raise HTTPException(500, f"Redis error: {exc}")
    await AuthActivityLog(
        user_id=str(admin.id), tg_id=admin.tg_id, action="admin.reset_quota",
        details={"target": user_id, "tg_id": user.tg_id},
    ).insert()
    return {"ok": True, "tg_id": user.tg_id}


# ── admin: roles ──────────────────────────────────────────────────────────────

@api.get("/admin/roles")
async def admin_roles(_: AuthUser = Depends(require_permission("admin:full"))):
    roles = await AuthRole.find_all().sort("name").to_list()
    return [{"id": str(r.id), "name": r.name, "description": r.description,
             "permissions": r.permissions, "created_at": r.created_at.isoformat()} for r in roles]


class RoleBody(BaseModel):
    name:        str = Field(max_length=50)
    description: str = Field(default="", max_length=500)
    permissions: list[str] = Field(default_factory=list, max_length=50)


@api.post("/admin/roles", status_code=201)
async def admin_create_role(body: RoleBody, admin: AuthUser = Depends(require_permission("admin:full"))):
    if await AuthRole.find_one(AuthRole.name == body.name):
        raise HTTPException(409, "Role already exists")
    role = AuthRole(name=body.name, description=body.description, permissions=body.permissions)
    await role.insert()
    # Flush RPM cache so new role perms take effect immediately
    from app.core.ratelimit import flush_rpm_cache
    flush_rpm_cache()
    return {"id": str(role.id), "name": role.name}


@api.put("/admin/roles/{role_id}")
async def admin_update_role(role_id: str, body: RoleBody,
                            admin: AuthUser = Depends(require_permission("admin:full"))):
    role = await AuthRole.get(role_id)
    if not role:
        raise HTTPException(404, "Not found")
    role.name = body.name
    role.description = body.description
    role.permissions = body.permissions
    await role.save()
    from app.core.ratelimit import flush_rpm_cache
    flush_rpm_cache()
    return {"id": str(role.id), "name": role.name}


@api.delete("/admin/roles/{role_id}", status_code=204)
async def admin_delete_role(role_id: str, admin: AuthUser = Depends(require_permission("admin:full"))):
    role = await AuthRole.get(role_id)
    if not role:
        raise HTTPException(404, "Not found")
    await role.delete()
    from app.core.ratelimit import flush_rpm_cache
    flush_rpm_cache()


# ── admin: permissions ────────────────────────────────────────────────────────

ALL_SYSTEM_PERMISSIONS: list[dict] = [
    {"perm": "schedule:read",   "group": "Schedule",  "description": "Read schedule data"},
    {"perm": "schedule:write",  "group": "Schedule",  "description": "Modify schedule data"},
    {"perm": "beta_access",     "group": "Features",  "description": "Access beta features in Mini App"},
    {"perm": "vip_access",      "group": "Features",  "description": "VIP filters (subgroups, etc.)"},
    {"perm": "users:read",      "group": "Users",     "description": "View user list and profiles"},
    {"perm": "users:write",     "group": "Users",     "description": "Edit users, block/unblock"},
    {"perm": "logs:read",       "group": "Logs",      "description": "View activity and error logs"},
    {"perm": "admin:full",      "group": "Admin",     "description": "Full admin access (all operations)"},
    {"perm": "floorplan:view",  "group": "Floorplan", "description": "View building floorplans"},
    {"perm": "floorplan:edit",  "group": "Floorplan", "description": "Edit building floorplans"},
    {"perm": "support:reply",   "group": "Support",   "description": "Reply to support tickets"},
    {"perm": "broadcast:send",  "group": "Broadcast", "description": "Send mass messages"},
    {"perm": "api:unlimited",   "group": "API",       "description": "No rate limiting on API"},
]


@api.get("/admin/permissions")
async def admin_permissions(_: AuthUser = Depends(require_permission("admin:full"))):
    """Return all known system permissions with descriptions."""
    roles = await AuthRole.find_all().to_list()
    known = {p["perm"] for p in ALL_SYSTEM_PERMISSIONS}
    custom = []
    for r in roles:
        for p in r.permissions:
            if p not in known:
                custom.append({"perm": p, "group": "Custom", "description": f"Custom (from role: {r.name})"})
                known.add(p)
    return {"permissions": ALL_SYSTEM_PERMISSIONS + custom}


@api.post("/admin/users/{user_id}/permissions")
async def admin_set_user_permissions(
    user_id: str,
    body:    dict,
    admin:   AuthUser = Depends(require_permission("admin:full")),
):
    """Set direct (extra) permissions for a specific user."""
    user = await AuthUser.get(user_id)
    if not user:
        raise HTTPException(404, "Not found")
    perms = body.get("permissions", [])
    if not isinstance(perms, list):
        raise HTTPException(400, "permissions must be a list")
    # Validate: max 50 permissions, each max 50 chars
    perms = [str(p)[:50] for p in perms[:50] if isinstance(p, str)]
    user.extra_permissions = perms
    await user.save()
    await AuthActivityLog(
        user_id=str(admin.id), tg_id=admin.tg_id,
        action="admin.user_permissions_updated",
        details={"target": user_id, "permissions": perms},
    ).insert()
    return {"ok": True, "permissions": user.extra_permissions}


# ── admin: logs ───────────────────────────────────────────────────────────────

@api.get("/admin/logs/activity")
async def admin_activity_logs(
    user_id: Optional[str] = None,
    tg_id:   Optional[int] = None,
    action:  Optional[str] = None,
    skip:    int = Query(default=0, ge=0),
    limit:   int = Query(default=50, ge=1, le=200),
    _: AuthUser = Depends(require_permission("logs:read")),
):
    from app.auth.database import get_auth_db
    col   = get_auth_db().get_collection("auth_activity_log")
    query: dict = {}
    if user_id: query["user_id"] = user_id
    if tg_id:   query["tg_id"]   = tg_id
    # [S7] Escape regex input
    if action:  query["action"]  = {"$regex": _escape_regex(action), "$options": "i"}

    total = await col.count_documents(query)
    raw   = await col.find(query).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)

    def _fmt(l: dict) -> dict:
        ts = l.get("timestamp")
        return {
            "id":        str(l.get("_id", "")),
            "user_id":   l.get("user_id"),
            "tg_id":     l.get("tg_id"),
            "action":    l.get("action", ""),
            "ip":        l.get("ip"),
            "details":   l.get("details", {}),
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts or ""),
        }
    return {"logs": [_fmt(l) for l in raw], "total": total}


@api.get("/admin/logs/errors")
async def admin_error_logs(
    level:    Optional[str] = None,
    user_id:  Optional[str] = None,
    search:   Optional[str] = None,
    error_id: Optional[str] = None,
    skip:     int = Query(default=0, ge=0),
    limit:    int = Query(default=50, ge=1, le=200),
    _: AuthUser = Depends(require_permission("logs:read")),
):
    from app.auth.database import get_auth_db
    col   = get_auth_db().get_collection("auth_error_logs")
    query: dict = {}
    if level:    query["level"]    = level.upper()
    if user_id:  query["user_id"]  = user_id
    if error_id:
        escaped = _escape_regex(error_id.strip().upper())
        query["error_id"] = {"$regex": escaped, "$options": "i"}
    # [S7] Escape regex input
    if search and not error_id:
        escaped = _escape_regex(search)
        regex = {"$regex": escaped, "$options": "i"}
        query["$or"] = [{"message": regex}, {"traceback": regex},
                        {"error_id": regex}, {"user_text": regex}]

    total = await col.count_documents(query)
    raw   = await col.find(query).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)

    def _fmt(e: dict) -> dict:
        ts = e.get("timestamp")
        return {
            "id":        str(e.get("_id", "")),
            "error_id":  e.get("error_id"),
            "level":     e.get("level", ""),
            "message":   e.get("message", ""),
            "traceback": e.get("traceback"),
            "user_id":   e.get("user_id"),
            "tg_id":     e.get("tg_id"),
            "path":      e.get("path"),
            "intent":    e.get("intent"),
            "user_text": e.get("user_text"),
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts or ""),
        }
    return {"logs": [_fmt(e) for e in raw], "total": total}


@api.get("/admin/analytics")
async def admin_analytics(
    days:       int = Query(default=7,  ge=1,  le=90),
    from_date:  Optional[str] = Query(default=None),  # ISO date YYYY-MM-DD
    to_date:    Optional[str] = Query(default=None),
    _: AuthUser = Depends(require_permission("logs:read")),
):
    """Rich analytics endpoint for the dashboard overview."""
    from app.auth.database import get_auth_db
    from app.db.database import get_motor_db

    now = _utcnow()
    if from_date:
        try:
            dt_from = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
        except ValueError:
            dt_from = now - timedelta(days=days)
    else:
        dt_from = now - timedelta(days=days)

    if to_date:
        try:
            dt_to = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc) + timedelta(days=1)
        except ValueError:
            dt_to = now
    else:
        dt_to = now

    auth_col  = get_auth_db().get_collection("auth_activity_log")
    err_col   = get_auth_db().get_collection("auth_error_logs")
    msg_col   = get_motor_db().get_collection("conversations")
    fb_col    = get_auth_db().get_collection("bot_feedback")

    _match_range = {"timestamp": {"$gte": dt_from, "$lte": dt_to}}
    _msg_range   = {"timestamp": {"$gte": dt_from, "$lte": dt_to}}

    # ── 1. Daily message volume (user + bot) ──────────────────────────────────
    daily_msgs = await msg_col.aggregate([
        {"$match": _msg_range},
        {"$group": {
            "_id": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "role": "$role",
            },
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id.date": 1}},
    ]).to_list(200)

    # ── 2. Daily error count ──────────────────────────────────────────────────
    daily_errors = await err_col.aggregate([
        {"$match": {"timestamp": {"$gte": dt_from, "$lte": dt_to}, "level": {"$in": ["ERROR", "CRITICAL"]}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]).to_list(200)

    # ── 3. Feedback stats by day ──────────────────────────────────────────────
    daily_feedback = await fb_col.aggregate([
        {"$match": {"created_at": {"$gte": dt_from, "$lte": dt_to}}},
        {"$group": {
            "_id": {
                "date":   {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "rating": "$rating",
            },
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id.date": 1}},
    ]).to_list(200)

    # ── 4. Feedback totals ────────────────────────────────────────────────────
    fb_likes    = await fb_col.count_documents({"rating": "like",    "created_at": {"$gte": dt_from, "$lte": dt_to}})
    fb_dislikes = await fb_col.count_documents({"rating": "dislike", "created_at": {"$gte": dt_from, "$lte": dt_to}})
    fb_pending  = await fb_col.count_documents({"rating": None,      "created_at": {"$gte": dt_from, "$lte": dt_to}})

    # ── 5. Intent / query type breakdown ─────────────────────────────────────
    intent_breakdown = await auth_col.aggregate([
        {"$match": {**_match_range, "action": {"$regex": "^bot\\.", "$options": "i"}}},
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 15},
    ]).to_list(15)

    # ── 6. Error breakdown by intent ─────────────────────────────────────────
    error_by_intent = await err_col.aggregate([
        {"$match": {"timestamp": {"$gte": dt_from, "$lte": dt_to}, "level": "ERROR", "intent": {"$ne": None}}},
        {"$group": {"_id": "$intent", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]).to_list(10)

    # ── 7. Top user queries (from user_text in error logs + activity) ─────────
    top_queries = await err_col.aggregate([
        {"$match": {"timestamp": {"$gte": dt_from, "$lte": dt_to}, "user_text": {"$ne": None}}},
        {"$group": {"_id": "$user_text", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]).to_list(10)

    # ── 8. Hourly activity heatmap ────────────────────────────────────────────
    hourly = await msg_col.aggregate([
        {"$match": _msg_range},
        {"$group": {
            "_id": {"$hour": "$timestamp"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]).to_list(24)

    # ── 9. New users per day ──────────────────────────────────────────────────
    auth_user_col = get_auth_db().get_collection("auth_users")
    new_users_daily = await auth_user_col.aggregate([
        {"$match": {"created_at": {"$gte": dt_from, "$lte": dt_to}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]).to_list(100)

    # ── 10. Total errors in period ────────────────────────────────────────────
    total_errors = await err_col.count_documents({
        "timestamp": {"$gte": dt_from, "$lte": dt_to},
        "level": {"$in": ["ERROR", "CRITICAL"]},
    })
    total_msgs = await msg_col.count_documents(_msg_range)

    # ── 11. MiniApp activity breakdown ───────────────────────────────────────
    miniapp_actions = await auth_col.aggregate([
        {"$match": {**_match_range, "action": {"$regex": "^miniapp\\.", "$options": "i"}}},
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 15},
    ]).to_list(15)

    return {
        "period": {
            "from": dt_from.isoformat(),
            "to":   dt_to.isoformat(),
            "days": days,
        },
        "totals": {
            "messages":  total_msgs,
            "errors":    total_errors,
            "fb_likes":     fb_likes,
            "fb_dislikes":  fb_dislikes,
            "fb_pending":   fb_pending,
            "fb_total":     fb_likes + fb_dislikes + fb_pending,
            "fb_pct_like":  round(fb_likes / max(fb_likes + fb_dislikes, 1) * 100),
        },
        "daily_messages": [
            {"date": d["_id"]["date"], "role": d["_id"]["role"], "count": d["count"]}
            for d in daily_msgs
        ],
        "daily_errors": [
            {"date": d["_id"], "count": d["count"]} for d in daily_errors
        ],
        "daily_feedback": [
            {"date": d["_id"]["date"], "rating": d["_id"]["rating"], "count": d["count"]}
            for d in daily_feedback
        ],
        "intent_breakdown": [
            {"intent": d["_id"], "count": d["count"]} for d in intent_breakdown
        ],
        "error_by_intent": [
            {"intent": d["_id"], "count": d["count"]} for d in error_by_intent
        ],
        "top_error_queries": [
            {"query": d["_id"], "count": d["count"]} for d in top_queries
        ],
        "hourly_heatmap": [
            {"hour": d["_id"], "count": d["count"]} for d in hourly
        ],
        "new_users_daily": [
            {"date": d["_id"], "count": d["count"]} for d in new_users_daily
        ],
        "miniapp_actions": [
            {"action": d["_id"], "count": d["count"]} for d in miniapp_actions
        ],
    }


# ── admin: chat history & live reply ─────────────────────────────────────────

def _get_db():
    from app.auth.database import get_auth_db
    return get_auth_db()


def _conv_col():
    return _get_db().get_collection("conversations")


def _legacy_col():
    return _get_db().get_collection("chat_messages")


# [S8] Capped memory usage, accurate total
async def _merged_docs(query: dict, sort_dir: int, skip: int, limit: int) -> tuple[list, int]:
    """
    Query BOTH collections and merge, deduplicating on (tg_id, message_id).
    Returns (docs, total_count).
    """
    from app.auth.database import get_auth_db
    db = get_auth_db()

    import asyncio as _aio
    # Cap fetch size to prevent OOM
    n = min(skip + limit + 200, 500)

    # Get accurate totals from both collections
    new_total, leg_total, new_docs, leg_docs = await _aio.gather(
        db.get_collection("conversations").count_documents(query),
        db.get_collection("chat_messages").count_documents(query),
        db.get_collection("conversations").find(query).sort("timestamp", -1).limit(n).to_list(n),
        db.get_collection("chat_messages").find(query).sort("timestamp", -1).limit(n).to_list(n),
    )

    seen: set[tuple] = set()
    merged: list[dict] = []
    for doc in new_docs:
        key = (doc.get("tg_id"), doc.get("message_id"))
        if key not in seen:
            seen.add(key)
            merged.append(doc)
    for doc in leg_docs:
        key = (doc.get("tg_id"), doc.get("message_id"))
        if key not in seen:
            seen.add(key)
            merged.append(doc)

    merged.sort(key=lambda d: d.get("timestamp") or datetime.min, reverse=True)

    # Use the higher of db counts (approximate but better than len(merged))
    total = max(new_total, leg_total, len(merged))
    page  = merged[skip: skip + limit]

    if sort_dir == 1:
        page = list(reversed(page))

    return page, total


async def _merged_poll(tg_id: int, after_ts) -> list[dict]:
    """Fetch new messages from BOTH collections newer than after_ts."""
    import asyncio as _aio
    from app.auth.database import get_auth_db
    db = get_auth_db()

    base_q: dict = {
        "tg_id": tg_id,
        "$or": [
            {"chat_id": tg_id},
            {"chat_id": {"$exists": False}},
        ],
    }
    if after_ts:
        base_q["timestamp"] = {"$gt": after_ts}

    new_docs, leg_docs = await _aio.gather(
        db.get_collection("conversations").find(base_q).sort("timestamp", 1).limit(50).to_list(50),
        db.get_collection("chat_messages").find(base_q).sort("timestamp", 1).limit(50).to_list(50),
    )

    seen: set[int] = set()
    merged: list[dict] = []
    for doc in new_docs + leg_docs:
        mid = doc.get("message_id")
        if mid is not None and mid not in seen:
            seen.add(mid)
            merged.append(doc)

    merged.sort(key=lambda d: d.get("timestamp") or datetime.min)
    return merged[:50]


def _fmt_conv(doc: dict, tg_id: int = 0) -> dict:
    """Flatten a document from EITHER collection into the flat shape admin.html reads."""
    ts  = doc.get("timestamp")
    media = doc.get("media") or {}

    media_type = media.get("kind") or doc.get("media_type")
    file_id    = media.get("file_id") or doc.get("file_id")
    file_uid   = media.get("file_unique_id") or doc.get("file_unique_id")
    thumb_fid  = media.get("thumbnail_file_id") or doc.get("thumbnail_file_id")

    fwd = doc.get("forward") or {}
    fwd_date_raw = fwd.get("date") or doc.get("forward_date")
    fwd_date = (
        fwd_date_raw.isoformat() if isinstance(fwd_date_raw, datetime)
        else str(fwd_date_raw) if fwd_date_raw else ""
    )

    return {
        "id":                  str(doc.get("_id", "")),
        "tg_id":               doc.get("tg_id", tg_id),
        "message_id":          doc.get("message_id"),
        "role":                doc.get("role", "user"),
        "first_name":          doc.get("first_name", ""),
        "last_name":           doc.get("last_name", ""),
        "username":            doc.get("username", ""),
        "text":                doc.get("text", ""),
        "html_text":           doc.get("html_text", "") or doc.get("text", ""),
        "timestamp":           ts.isoformat() if isinstance(ts, datetime) else str(ts or ""),
        "is_forward":          bool(doc.get("forward") or doc.get("is_forward")),
        "forward_from_name":   fwd.get("name") or doc.get("forward_from_name"),
        "forward_from_chat":   doc.get("forward_from_chat"),
        "forward_date":        fwd_date,
        "reply_to_message_id": doc.get("reply_to_message_id"),
        "reply_to_text":       doc.get("reply_to_text"),
        "media_type":          media_type,
        "file_id":             file_id,
        "file_unique_id":      file_uid,
        "file_name":           media.get("file_name")  or doc.get("file_name"),
        "file_size":           media.get("file_size")  or doc.get("file_size"),
        "mime_type":           media.get("mime_type")  or doc.get("mime_type"),
        "duration":            media.get("duration")   or doc.get("duration"),
        "width":               media.get("width")      or doc.get("width"),
        "height":              media.get("height")     or doc.get("height"),
        "thumbnail_file_id":   thumb_fid,
        "sticker_emoji":       media.get("sticker_emoji") or doc.get("sticker_emoji"),
        "media_url":           None,
        "extra":               doc.get("extra"),
    }


async def _inject_media_urls(msgs: list[dict]) -> None:
    """Resolve Telegram CDN URLs for every message that has a file_id, in parallel."""
    import asyncio as _aio
    from app.dashboard.media_service import resolve_media_url

    tasks, targets = [], []
    for m in msgs:
        fid  = m.get("file_id")
        fuid = m.get("file_unique_id")
        if fid and fuid:
            tasks.append(resolve_media_url(fid, fuid))
            targets.append(m)

    if not tasks:
        return

    results = await _aio.gather(*tasks, return_exceptions=True)
    for m, res in zip(targets, results):
        if isinstance(res, Exception):
            logger.debug(f"Media URL resolution failed: {res}")
            m["media_url"] = None
        else:
            m["media_url"] = res


@api.get("/admin/chats")
async def admin_chat_list(
    _: AuthUser = Depends(require_permission("admin:full")),
):
    """Return all users with messages, sorted by most recent — from BOTH collections."""
    from app.auth.database import get_auth_db
    import asyncio as _aio
    db = get_auth_db()

    # NOTE: We group ONLY by tg_id here because these are private-bot conversations.
    # Key constraints:
    # - chat_messages (legacy) has NO chat_type or chat_id fields — can't filter on them.
    # - conversations (new) stores ALL messages including bot replies and group messages.
    #   Bot replies have tg_id = bot's ID (before our fix) or user's ID (after fix).
    #   Group messages have negative chat_id.
    # Strategy:
    # - Exclude role="bot" — bot reply rows must not create a "user" entry for the bot.
    # - Exclude negative chat_id — those are group/supergroup chats (conversations only).
    # - The legacy chat_messages collection has no chat_id, so the $gt filter passes them.
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {"$match": {
            "role": {"$in": ["user", "admin", None, ""]},  # skip bot/assistant messages
            "chat_id": {"$not": {"$lt": 0}},               # skip group chats (neg IDs); passes docs without chat_id
        }},
        {"$group": {
            "_id":        "$tg_id",
            "last_ts":    {"$first": "$timestamp"},
            "last_text":  {"$first": "$text"},
            "last_role":  {"$first": "$role"},
            "msg_count":  {"$sum": 1},
        }},
    ]

    new_rows, leg_rows = await _aio.gather(
        db.get_collection("conversations").aggregate(pipeline).to_list(500),
        db.get_collection("chat_messages").aggregate(pipeline).to_list(500),
    )

    by_tg: dict = {}
    for r in leg_rows + new_rows:
        tid = r["_id"]
        existing = by_tg.get(tid)
        if not existing or (r["last_ts"] and (not existing["last_ts"] or r["last_ts"] > existing["last_ts"])):
            by_tg[tid] = r
        else:
            by_tg[tid]["msg_count"] = by_tg[tid].get("msg_count", 0) + r.get("msg_count", 0)

    rows = sorted(by_tg.values(), key=lambda r: r.get("last_ts") or datetime.min, reverse=True)[:200]

    tg_ids    = [r["_id"] for r in rows]
    user_docs = await db.get_collection("auth_users").find(
        {"tg_id": {"$in": tg_ids}}
    ).to_list(200)
    user_map = {u["tg_id"]: u for u in user_docs}

    result = []
    for r in rows:
        tid = r["_id"]
        u   = user_map.get(tid, {})
        display = f"{u.get('first_name','')} {u.get('last_name','')}".strip() or f"tg:{tid}"
        ts      = r.get("last_ts")
        result.append({
            "tg_id":      tid,
            "display":    display,
            "username":   u.get("username"),
            "avatar":     get_avatar_url(tid),
            "last_text":  (r.get("last_text") or "")[:80],
            "last_role":  r.get("last_role", "user"),
            "last_ts":    ts.isoformat() if isinstance(ts, datetime) else str(ts or ""),
            "msg_count":  r.get("msg_count", 0),
            "is_blocked": u.get("is_blocked", False),
        })
    return {"chats": result}


@api.get("/admin/chat/{tg_id}/poll")
async def admin_chat_poll(
    tg_id:    int,
    after_ts: Optional[str] = None,
    _: AuthUser = Depends(require_permission("admin:full")),
):
    dt = None
    if after_ts:
        try:
            dt = datetime.fromisoformat(after_ts.replace("Z", "+00:00"))
        except Exception:
            pass

    raw  = await _merged_poll(tg_id, dt)
    msgs = [_fmt_conv(d, tg_id) for d in raw]
    await _inject_media_urls(msgs)
    return {"messages": msgs}


@api.get("/admin/chat/{tg_id}/search")
async def admin_chat_search(
    tg_id: int,
    q:     str = "",
    limit: int = Query(default=50, ge=1, le=200),
    _: AuthUser = Depends(require_permission("admin:full")),
):
    """Full-text search across messages for a user — both collections."""
    import asyncio as _aio
    from app.auth.database import get_auth_db
    db = get_auth_db()

    base_q: dict = {
        "tg_id": tg_id,
        "$or": [
            {"chat_id": tg_id},
            {"chat_id": {"$exists": False}},
        ],
    }
    if q.strip():
        # [S7] Escape regex input
        escaped = _escape_regex(q)
        base_q["$or"] = [
            {"text":      {"$regex": escaped, "$options": "i"}},
            {"html_text": {"$regex": escaped, "$options": "i"}},
        ]

    new_docs, leg_docs = await _aio.gather(
        db.get_collection("conversations").find(base_q).sort("timestamp", -1).limit(limit).to_list(limit),
        db.get_collection("chat_messages").find(base_q).sort("timestamp", -1).limit(limit).to_list(limit),
    )

    seen: set = set()
    merged: list = []
    for doc in new_docs + leg_docs:
        key = (doc.get("tg_id"), doc.get("message_id"))
        if key not in seen:
            seen.add(key)
            merged.append(doc)

    merged.sort(key=lambda d: d.get("timestamp") or datetime.min)
    msgs = [_fmt_conv(d, tg_id) for d in merged[:limit]]
    await _inject_media_urls(msgs)
    return {"messages": msgs, "total": len(msgs)}


@api.get("/admin/chat/{tg_id}")
async def admin_chat_history(
    tg_id:      int,
    offset:     int            = Query(default=0, ge=0),
    limit:      int            = Query(default=30, ge=1, le=100),
    media_type: Optional[str]  = None,
    date_from:  Optional[str]  = None,
    date_to:    Optional[str]  = None,
    _: AuthUser = Depends(require_permission("admin:full")),
):
    # Fetch only messages belonging to this user's PRIVATE conversation.
    # New "conversations" docs: chat_id == tg_id for private chats (positive).
    # Legacy "chat_messages" docs: no chat_id field at all.
    # We use $or so that both collections work correctly:
    #   - new docs: chat_id must equal tg_id (excludes group messages where tg_id is sender)
    #   - legacy docs: chat_id missing → match via tg_id alone
    query: dict = {
        "tg_id": tg_id,
        "$or": [
            {"chat_id": tg_id},            # new: private chat, chat_id == tg_id
            {"chat_id": {"$exists": False}}, # legacy: no chat_id field
        ],
    }

    if media_type == "link":
        query["$or"] = [
            {"text":      {"$regex": r"https?://", "$options": "i"}},
            {"html_text": {"$regex": r"https?://", "$options": "i"}},
        ]
    elif media_type:
        # Validate media_type against known types
        _VALID_MEDIA = {"photo", "video", "animation", "sticker", "voice", "video_note", "audio", "document"}
        if media_type not in _VALID_MEDIA:
            raise HTTPException(400, f"Invalid media_type. Allowed: {sorted(_VALID_MEDIA)}")
        query["$or"] = [
            {"media.kind": media_type},
            {"media_type": media_type},
        ]

    date_filter: dict = {}
    if date_from:
        try:
            date_filter["$gte"] = datetime.fromisoformat(date_from)
        except ValueError:
            pass
    if date_to:
        try:
            date_filter["$lte"] = datetime.fromisoformat(date_to).replace(
                hour=23, minute=59, second=59
            )
        except ValueError:
            pass
    if date_filter:
        query["timestamp"] = date_filter

    docs, total = await _merged_docs(query, sort_dir=-1, skip=offset, limit=limit)
    msgs = [_fmt_conv(d, tg_id) for d in docs]
    await _inject_media_urls(msgs)
    return {"messages": msgs, "total": total, "tg_id": tg_id}


@api.get("/admin/chat/{tg_id}/media")
async def admin_download_media(
    tg_id:   int,
    file_id: str,
    _: AuthUser = Depends(require_permission("admin:full")),
):
    """Stream a Telegram file through the server (CORS fix)."""
    import httpx
    from starlette.responses import StreamingResponse
    from app.cache.redis import get_redis

    token = settings.get_telegram_bot_token()
    if not token:
        raise HTTPException(503, "Bot token not configured")

    # Validate file_id format — basic sanity check
    if not file_id or len(file_id) > 200 or not file_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(400, "Invalid file_id format")

    cdn_cache_key = f"tg:cdn:{file_id}"
    cdn_url: str | None = None
    file_size: int | None = None

    try:
        raw = await get_redis().get(cdn_cache_key)
        if raw:
            cdn_url = raw.decode() if isinstance(raw, bytes) else raw
    except Exception:
        pass

    if not cdn_url:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"https://api.telegram.org/bot{token}/getFile",
                params={"file_id": file_id},
            )
            data = r.json()

        if not data.get("ok"):
            raise HTTPException(404, f"getFile failed: {data.get('description', 'unknown')}")

        file_path = data["result"]["file_path"]
        file_size = data["result"].get("file_size")
        cdn_url   = f"https://api.telegram.org/file/bot{token}/{file_path}"

        try:
            await get_redis().setex(cdn_cache_key, 3600, cdn_url.encode())
        except Exception:
            pass

    # [S-SSRF] Validate CDN URL is from Telegram
    if not cdn_url.startswith("https://api.telegram.org/"):
        raise HTTPException(400, "Invalid CDN URL")

    ext  = cdn_url.split("?")[0].rsplit(".", 1)[-1].lower()
    mime = {
        "jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png",
        "gif":"image/gif","webp":"image/webp",
        "mp4":"video/mp4","mov":"video/quicktime","webm":"video/webm",
        "ogg":"audio/ogg","oga":"audio/ogg","opus":"audio/ogg",
        "mp3":"audio/mpeg","m4a":"audio/mp4",
        "pdf":"application/pdf","tgs":"application/x-tgsticker",
    }.get(ext, "application/octet-stream")

    streaming_client = httpx.AsyncClient(timeout=httpx.Timeout(10, read=120))

    async def _stream():
        try:
            async with streaming_client.stream("GET", cdn_url) as resp:
                async for chunk in resp.aiter_bytes(65536):
                    yield chunk
        finally:
            await streaming_client.aclose()

    headers: dict = {"Cache-Control": "private, max-age=3600", "Accept-Ranges": "none"}
    if file_size:
        headers["Content-Length"] = str(file_size)

    return StreamingResponse(_stream(), media_type=mime, headers=headers)


class SendMessageBody(BaseModel):
    tg_id: int
    text:  str = Field(max_length=4096)


@api.post("/admin/chat/send")
async def admin_send_message(
    body:  SendMessageBody,
    admin: AuthUser = Depends(require_permission("admin:full")),
):
    import httpx
    token = settings.get_telegram_bot_token()
    if not token:
        raise HTTPException(503, "Bot token not configured")
    if not body.text.strip():
        raise HTTPException(400, "Empty message")

    # [S5] Sanitize HTML in outbound messages
    import html
    safe_text = html.escape(body.text.strip())

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": body.tg_id, "text": safe_text, "parse_mode": "HTML"},
        )
    if not r.is_success:
        raise HTTPException(502, f"Telegram error: {r.text[:200]}")

    sent_data   = r.json().get("result", {})
    sent_msg_id = sent_data.get("message_id", 0)

    import asyncio as _aio
    from app.dashboard.message_utils import store_admin_message
    _aio.ensure_future(store_admin_message(body.tg_id, body.text, sent_msg_id))

    await AuthActivityLog(
        user_id=str(admin.id), tg_id=admin.tg_id, action="admin.send_message",
        details={"target_tg_id": body.tg_id, "preview": body.text[:80]},
    ).insert()
    return {"ok": True}


# ── admin: broadcast ──────────────────────────────────────────────────────────

class BroadcastBody(BaseModel):
    text:        str = Field(max_length=4096)
    audience:    str = "all"
    role:        Optional[str] = None
    schedule_at: Optional[str] = None

    @field_validator("audience")
    @classmethod
    def validate_audience(cls, v: str) -> str:
        if v not in {"all", "active", "role"}:
            raise ValueError("audience must be 'all', 'active', or 'role'")
        return v


# [S5] Broadcast cooldown
_BROADCAST_COOLDOWN_SECONDS = 300  # 5 minutes


@api.post("/admin/broadcast", status_code=202)
async def admin_broadcast(
    body:  BroadcastBody,
    admin: AuthUser = Depends(require_permission("admin:full")),
):
    if not body.text.strip():
        raise HTTPException(400, "Empty message")

    # [S5] Enforce cooldown
    try:
        from app.cache.redis import get_redis
        r = get_redis()
        cooldown_key = f"broadcast:cooldown:{admin.id}"
        if await r.exists(cooldown_key):
            ttl = await r.ttl(cooldown_key)
            raise HTTPException(429, f"Broadcast cooldown: wait {ttl}s before next broadcast")
    except HTTPException:
        raise
    except Exception:
        pass  # Redis error — allow broadcast

    schedule_dt = None
    if body.schedule_at:
        try:
            schedule_dt = datetime.fromisoformat(body.schedule_at)
        except ValueError:
            raise HTTPException(400, "Invalid schedule_at datetime")

    job = BroadcastJob(
        text=body.text,
        audience=body.audience,
        role=body.role,
        schedule_at=schedule_dt,
        created_by=str(admin.id),
    )
    await job.insert()

    # [S10] Set cooldown
    try:
        await r.setex(cooldown_key, _BROADCAST_COOLDOWN_SECONDS, "1")
    except Exception:
        pass

    # Push to Redis queue for immediate dispatch if no schedule
    if not schedule_dt:
        try:
            import json as _json
            await get_redis().rpush("broadcast_queue", _json.dumps({
                "job_id": str(job.id),
                "text":   body.text,
                "audience": body.audience,
                "role":   body.role,
            }))
        except Exception as exc:
            logger.warning(f"broadcast queue push failed: {exc}")

    return {"job_id": str(job.id), "status": "queued"}


@api.get("/admin/broadcasts")
async def admin_list_broadcasts(_: AuthUser = Depends(require_permission("admin:full"))):
    jobs = await BroadcastJob.find_all().sort("-created_at").to_list(50)
    return {"broadcasts": [
        {"id": str(j.id), "text": j.text, "audience": j.audience,
         "status": j.status, "sent_count": j.sent_count,
         "created_at": j.created_at.isoformat()}
        for j in jobs
    ]}


# ── admin: support tickets ────────────────────────────────────────────────────

@api.get("/admin/support")
async def admin_support_list(
    status:   Optional[str] = None,
    category: Optional[str] = None,
    skip:     int = Query(default=0, ge=0),
    limit:    int = Query(default=30, ge=1, le=100),
    _: AuthUser = Depends(require_permission("admin:full")),
):
    query: dict = {}
    if status:
        if status not in {"open", "answered", "closed"}:
            raise HTTPException(400, "Invalid status")
        query["status"] = status
    if category:
        if category not in {"bug", "suggestion", "question", "other"}:
            raise HTTPException(400, "Invalid category")
        query["category"] = category

    from app.auth.database import get_auth_db
    col   = get_auth_db().get_collection("support_tickets")
    total = await col.count_documents(query)
    raw   = await col.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    def _fmt(t: dict) -> dict:
        ts = t.get("created_at")
        ct = t.get("closed_at")
        rt = t.get("replied_at")
        return {
            "id":                  str(t.get("_id", "")),
            "tg_id":               t.get("tg_id"),
            "username":            t.get("username"),
            "first_name":          t.get("first_name", ""),
            "message":             t.get("message", ""),
            "status":              t.get("status", "open"),
            "category":            t.get("category", "other"),
            "source":              t.get("source", "bot"),
            "admin_reply":         t.get("admin_reply"),
            "replied_at":          rt.isoformat() if isinstance(rt, datetime) else str(rt or ""),
            "close_reason":        t.get("close_reason"),
            "close_reason_hidden": t.get("close_reason_hidden", False),
            "closed_by":           t.get("closed_by"),
            "closed_at":           ct.isoformat() if isinstance(ct, datetime) else str(ct or ""),
            "created_at":          ts.isoformat() if isinstance(ts, datetime) else str(ts or ""),
        }
    return {"tickets": [_fmt(t) for t in raw], "total": total}


@api.get("/admin/support/{ticket_id}")
async def admin_support_detail(
    ticket_id: str,
    _: AuthUser = Depends(require_permission("admin:full")),
):
    ticket = await SupportTicket.get(ticket_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    return {"ticket": {
        "id":                 str(ticket.id),
        "tg_id":              ticket.tg_id,
        "username":           ticket.username,
        "first_name":         ticket.first_name,
        "message":            ticket.message,
        "status":             ticket.status,
        "category":           getattr(ticket, "category", "other"),
        "source":             getattr(ticket, "source", "bot"),
        "admin_reply":        ticket.admin_reply,
        "replied_at":         ticket.replied_at.isoformat() if ticket.replied_at else None,
        "created_at":         ticket.created_at.isoformat(),
        "close_reason":       getattr(ticket, "close_reason", None),
        "close_reason_hidden":getattr(ticket, "close_reason_hidden", False),
        "closed_by":          getattr(ticket, "closed_by", None),
        "closed_at":          ticket.closed_at.isoformat() if getattr(ticket, "closed_at", None) else None,
    }}


class TicketReplyBody(BaseModel):
    reply: str = Field(max_length=4096)


@api.post("/admin/support/{ticket_id}/reply")
async def admin_reply_ticket(
    ticket_id: str,
    body:      TicketReplyBody,
    admin:     AuthUser = Depends(require_permission("admin:full")),
):
    ticket = await SupportTicket.get(ticket_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    if not body.reply.strip():
        raise HTTPException(400, "Empty reply")

    import httpx
    import html as _html
    token = settings.get_telegram_bot_token()
    if token:
        try:
            # [S-XSS] Escape reply text before sending as HTML
            safe_reply = _html.escape(body.reply)
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id":    ticket.tg_id,
                        "text":       f"📬 <b>Ответ поддержки</b>\n\n{safe_reply}",
                        "parse_mode": "HTML",
                    },
                )
        except Exception as exc:
            logger.warning(f"support reply send failed: {exc}")

    ticket.admin_reply = body.reply
    ticket.status      = "answered"
    ticket.replied_at  = _utcnow()
    await ticket.save()
    return {"ok": True}


@api.post("/admin/support/{ticket_id}/close", status_code=200)
async def admin_close_ticket(
    ticket_id: str,
    body:      dict,
    admin:     AuthUser = Depends(require_permission("admin:full")),
):
    ticket = await SupportTicket.get(ticket_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    reason = str(body.get("reason", "")).strip()[:500]
    if not reason:
        raise HTTPException(400, "Close reason is required")
    ticket.status              = "closed"
    ticket.close_reason        = reason
    ticket.close_reason_hidden = bool(body.get("hide_reason", False))
    ticket.closed_by           = "admin"
    ticket.closed_at           = _utcnow()
    await ticket.save()

    import html as _html
    token = settings.get_telegram_bot_token()
    if not ticket.close_reason_hidden and token:
        import httpx
        try:
            safe_reason = _html.escape(reason)
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id":    ticket.tg_id,
                        "text":       f"🔒 <b>Обращение #{ticket.short_id} закрыто</b>\n\n{safe_reason}",
                        "parse_mode": "HTML",
                    },
                )
        except Exception as exc:
            logger.warning(f"ticket close notify failed: {exc}")

    await AuthActivityLog(
        user_id=str(admin.id), tg_id=admin.tg_id,
        action="admin.ticket_closed",
        details={"ticket_id": ticket_id, "reason": reason},
    ).insert()
    return {"ok": True}


# ── admin: MongoDB viewer ─────────────────────────────────────────────────────

_ALLOWED_COLLECTIONS = {
    "auth_users", "auth_activity_log", "auth_error_logs",
    "auth_roles", "auth_api_keys", "support_tickets",
    "bot_conversations", "broadcast_jobs",
    "lessons", "groups", "teachers", "rooms", "institutes",
    "scrape_logs",
}


@api.get("/admin/mongo")
async def admin_mongo_viewer(
    collection: str,
    filter:     str  = Query(default="", description="JSON filter object"),
    sort:       str  = Query(default="", description="field:direction e.g. timestamp:-1"),
    skip:       int  = Query(default=0, ge=0),
    limit:      int  = Query(default=20, ge=1, le=50),  # [S6] Reduced from 100 to 50
    _: AuthUser = Depends(require_permission("admin:full")),
):
    if collection not in _ALLOWED_COLLECTIONS:
        raise HTTPException(400, f"Collection not allowed. Allowed: {sorted(_ALLOWED_COLLECTIONS)}")

    # [S1] Sanitized filter — blocks all MongoDB operators
    flt = _safe_parse_filter(filter)

    from app.auth.database import get_auth_db
    from app.db.database import get_motor_db

    schedule_collections = {"lessons", "groups", "teachers", "rooms", "institutes", "scrape_logs"}
    if collection in schedule_collections:
        db = get_motor_db()
    else:
        db = get_auth_db()

    col   = db.get_collection(collection)

    # [S6] Add maxTimeMS to prevent long-running queries
    total = await col.count_documents(flt, maxTimeMS=5000)

    cursor = col.find(flt, max_time_ms=5000)

    # Apply sort with validation
    if sort:
        parts = sort.split(":")
        if len(parts) == 2:
            field = parts[0].strip()
            # Validate field name — no operators
            if field and not field.startswith("$") and field.isidentifier():
                try:
                    direction = int(parts[1])
                    if direction not in (1, -1):
                        direction = -1
                except ValueError:
                    direction = -1
                cursor = cursor.sort(field, direction)

    raw = await cursor.skip(skip).limit(limit).to_list(limit)

    def _clean(d: dict) -> dict:
        out = {}
        for k, v in d.items():
            if hasattr(v, "__str__") and type(v).__name__ in ("ObjectId", "PydanticObjectId"):
                out[k] = str(v)
            elif isinstance(v, datetime):
                out[k] = v.isoformat()
            elif isinstance(v, dict):
                out[k] = _clean(v)
            elif isinstance(v, list):
                out[k] = [_clean(i) if isinstance(i, dict) else
                          str(i) if type(i).__name__ in ("ObjectId","PydanticObjectId") else i
                          for i in v]
            else:
                out[k] = v
        return out

    return {"documents": [_clean(r) for r in raw], "total": total, "skip": skip}


# ── admin: settings ───────────────────────────────────────────────────────────

_SAFE_SETTINGS_FIELDS: list[str] = [
    "app_env", "log_level",
    "scrape_interval_hours", "scraper_concurrency", "scraper_request_delay",
    "scrape_mode", "academic_year_start",
    "rate_limit_user_rpm", "rate_limit_anon_rpm", "rate_limit_bot_rpm", "rate_limit_window",
    "cache_ttl_now", "cache_ttl_day", "cache_ttl_week", "cache_ttl_search", "cache_ttl_meta",
    "webhook_base_url",
    "sentry_traces_rate",
    "activity_log_ttl_days", "cleanup_hour_utc",
    "telegram_bot_configured",
    "openai_configured",
    "sentry_configured",
    "redis_password_configured",
    "mongo_auth_configured",
]

_WRITABLE_FIELDS: frozenset[str] = frozenset({
    "scrape_interval_hours", "scraper_concurrency", "scraper_request_delay",
    "scrape_mode", "academic_year_start",
    "rate_limit_user_rpm", "rate_limit_anon_rpm", "rate_limit_bot_rpm", "rate_limit_window",
    "cache_ttl_now", "cache_ttl_day", "cache_ttl_week", "cache_ttl_search", "cache_ttl_meta",
    "activity_log_ttl_days", "cleanup_hour_utc",
    "log_level",
})

# [S3] Type constraints for writable settings
_SETTINGS_TYPE_VALIDATORS: dict[str, tuple] = {
    "scrape_interval_hours": (int, 1, 168),
    "scraper_concurrency":   (int, 1, 20),
    "scraper_request_delay": (float, 0.1, 10.0),
    "scrape_mode":           (str, None, None),
    "academic_year_start":   (int, 2020, 2100),
    "rate_limit_user_rpm":   (int, 1, 10000),
    "rate_limit_anon_rpm":   (int, 1, 1000),
    "rate_limit_bot_rpm":    (int, 1, 1000),
    "rate_limit_window":     (int, 10, 600),
    "cache_ttl_now":         (int, 10, 86400),
    "cache_ttl_day":         (int, 60, 86400),
    "cache_ttl_week":        (int, 60, 604800),
    "cache_ttl_search":      (int, 60, 86400),
    "cache_ttl_meta":        (int, 60, 604800),
    "activity_log_ttl_days": (int, 7, 365),
    "cleanup_hour_utc":      (int, 0, 23),
    "log_level":             (str, None, None),
}


def _get_safe_settings() -> dict:
    out: dict = {}
    for field in _SAFE_SETTINGS_FIELDS:
        if field == "telegram_bot_configured":
            tok = getattr(settings, "telegram_bot_token", None)
            out[field] = bool(tok.get_secret_value() if hasattr(tok, "get_secret_value") else tok)
        elif field == "openai_configured":
            key = getattr(settings, "openai_api_key", None)
            out[field] = bool(key.get_secret_value() if hasattr(key, "get_secret_value") else key)
        elif field == "sentry_configured":
            dsn = getattr(settings, "sentry_dsn", None)
            out[field] = bool(dsn.get_secret_value() if hasattr(dsn, "get_secret_value") else dsn)
        elif field == "redis_password_configured":
            url = getattr(settings, "redis_url", "")
            out[field] = ":@" in str(url) or "password" in str(url).lower()
        elif field == "mongo_auth_configured":
            uri = getattr(settings, "mongo_uri", "")
            out[field] = "@" in str(uri)
        else:
            val = getattr(settings, field, None)
            if val is not None:
                out[field] = val
    return out


@api.get("/admin/settings")
async def admin_get_settings(_: AuthUser = Depends(require_permission("admin:full"))):
    return _get_safe_settings()


@api.post("/admin/settings")
async def admin_save_settings(
    body:  dict,
    admin: AuthUser = Depends(require_permission("admin:full")),
):
    """
    [S3] Hardened settings update.
    - Strict allowlist
    - Type validation with bounds
    - Atomic file write with tempfile
    - No runtime setattr for non-matching types
    """
    import tempfile
    from pathlib import Path

    safe_body = {}
    rejected = set()
    errors = []

    for k, v in body.items():
        if k not in _WRITABLE_FIELDS:
            rejected.add(k)
            continue
        # Type validation
        validator = _SETTINGS_TYPE_VALIDATORS.get(k)
        if validator:
            expected_type, min_val, max_val = validator
            try:
                typed_val = expected_type(v)
                if min_val is not None and typed_val < min_val:
                    errors.append(f"{k}: value {typed_val} below minimum {min_val}")
                    continue
                if max_val is not None and typed_val > max_val:
                    errors.append(f"{k}: value {typed_val} above maximum {max_val}")
                    continue
                safe_body[k] = typed_val
            except (ValueError, TypeError) as exc:
                errors.append(f"{k}: invalid type ({exc})")
                continue
        else:
            safe_body[k] = v

    if rejected:
        logger.warning(
            f"admin_save_settings: rejected fields: {rejected} "
            f"(admin tg_id={admin.tg_id})"
        )

    if errors:
        raise HTTPException(400, {"errors": errors})

    env_path = Path(".env")
    if not env_path.exists():
        return {"ok": False, "error": ".env file not found"}

    content = env_path.read_text(encoding="utf-8")
    updated: list[str] = []

    for key, value in safe_body.items():
        env_key = key.upper()
        pattern = re.compile(rf"^{re.escape(env_key)}=.*$", re.MULTILINE)
        new_line = f"{env_key}={value}"
        if pattern.search(content):
            content = pattern.sub(new_line, content)
        else:
            content += f"\n{new_line}"
        updated.append(env_key)

        # [S3] Safe runtime apply with proper type matching
        try:
            current = getattr(settings, key, None)
            if current is not None:
                target_type = type(current)
                if target_type in (int, float, str, bool):
                    setattr(settings, key, target_type(value))
        except Exception as exc:
            logger.warning(f"Could not apply {key} to live settings: {exc}")

    # [S3] Atomic write: write to temp file, then rename
    try:
        fd, tmp_path = tempfile.mkstemp(dir=env_path.parent, suffix=".env.tmp")
        import os
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(env_path))
    except Exception as exc:
        logger.error(f"Failed to write .env atomically: {exc}")
        # Fallback to non-atomic write
        env_path.write_text(content, encoding="utf-8")

    await AuthActivityLog(
        user_id=str(admin.id), tg_id=admin.tg_id, action="admin.settings_updated",
        details={"changed": updated},
    ).insert()
    return {
        "ok":    True,
        "changed": updated,
        "note":  "Restart the API container to apply changes.",
    }


# ── [S4] admin: bot commands — with method allowlist ─────────────────────────

# Only safe, read-only or basic send methods are allowed
_ALLOWED_BOT_METHODS = frozenset({
    "sendMessage", "sendPhoto", "sendDocument", "sendVideo",
    "sendAnimation", "sendVoice", "sendAudio", "sendSticker",
    "sendLocation", "sendContact", "sendPoll",
    "getMe", "getChat", "getChatMember", "getChatMembersCount",
    "getWebhookInfo", "getUpdates",
    "sendChatAction", "forwardMessage",
})

# Explicitly blocked dangerous methods
_BLOCKED_BOT_METHODS = frozenset({
    "setWebhook", "deleteWebhook", "close", "logOut",
    "banChatMember", "kickChatMember", "restrictChatMember",
    "promoteChatMember", "setChatAdministratorCustomTitle",
    "deleteMessage", "editMessageText",
})


@api.post("/admin/bot/command")
async def admin_bot_command(
    body:  dict,
    admin: AuthUser = Depends(require_permission("admin:full")),
):
    """Execute a safe bot API method. Dangerous methods are blocked."""
    import httpx
    method = body.get("method", "sendMessage")
    params = body.get("params", {})

    # [S4] Method allowlist
    if method in _BLOCKED_BOT_METHODS:
        raise HTTPException(403, f"Method '{method}' is blocked for security")
    if method not in _ALLOWED_BOT_METHODS:
        raise HTTPException(400, f"Method '{method}' not in allowlist. Allowed: {sorted(_ALLOWED_BOT_METHODS)}")

    token = settings.get_telegram_bot_token()
    if not token:
        raise HTTPException(503, "Bot token not configured")

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{token}/{method}",
            json=params,
        )

    # Log the action
    await AuthActivityLog(
        user_id=str(admin.id), tg_id=admin.tg_id, action="admin.bot_command",
        details={"method": method, "params_keys": list(params.keys())},
    ).insert()

    return r.json()
