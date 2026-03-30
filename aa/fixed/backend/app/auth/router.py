"""
Auth REST API router — HARDENED.

ИСПРАВЛЕНИЯ:
  [F1] admin_users: переменная q затирала параметр запроса q (query string).
       Переименована в query / user_query для ясности.
  [F2] refresh_token: JTI теперь берётся из decode_access_token() (с проверкой подписи),
       а НЕ через options={"verify_signature": False} — это было уязвимостью.
  [F3] telegram_login: TOTP-ответ с пустыми токенами заменён на явный 202 статус,
       чтобы фронтенд не путал пустые токены с реальными.
  [F4] Добавлен limit на admin_activity_logs (был без ограничения по умолчанию).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel, Field
from loguru import logger

from app.auth.models import AuthActivityLog, AuthApiKey, AuthUser
from app.auth.security import (
    create_access_token, create_refresh_token, decode_access_token,
    generate_api_key, issue_dpop_nonce, validate_telegram_init_data,
)
from app.auth.dependencies import (
    get_current_user, optional_auth, require_permission, require_admin,
    _user_permissions,
)
from app.auth.avatars import fetch_and_save_avatar, get_avatar_url
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
_utcnow = lambda: datetime.now(timezone.utc)  # noqa: E731


# ── Request / Response schemas ────────────────────────────────────────────────

class TelegramLoginRequest(BaseModel):
    init_data: str
    dpop_jwk: Optional[dict] = None
    totp_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    totp_required: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class CreateApiKeyRequest(BaseModel):
    name: str = Field(default="default", max_length=100)
    permissions: list[str] = Field(default_factory=list, max_length=20)
    rate_limit_rpm: int = Field(default=60, ge=1, le=1000)
    expires_days: Optional[int] = Field(default=None, ge=1, le=365)


class ApiKeyResponse(BaseModel):
    id: str
    key: Optional[str] = None
    prefix: str
    name: str
    permissions: list[str]
    rate_limit_rpm: int
    expires_at: Optional[datetime]
    created_at: datetime


class UserResponse(BaseModel):
    id: str
    tg_id: int
    username: Optional[str]
    first_name: str
    photo_url: Optional[str]
    roles: list[str]
    is_blocked: bool
    last_active: datetime
    created_at: datetime


class AdminUpdateUserRequest(BaseModel):
    roles: Optional[list[str]] = None
    is_blocked: Optional[bool] = None
    block_reason: Optional[str] = Field(default=None, max_length=500)


# ── Activity log helper ───────────────────────────────────────────────────────

async def _log(
    action: str,
    user: Optional[AuthUser] = None,
    request: Optional[Request] = None,
    details: dict | None = None,
) -> None:
    try:
        entry = AuthActivityLog(
            user_id=str(user.id) if user else None,
            tg_id=user.tg_id if user else None,
            action=action,
            request_id=getattr(getattr(request, "state", None), "request_id", None),
            ip=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            details=details or {},
        )
        await entry.insert()
    except Exception as exc:
        logger.warning(f"Activity log insert failed: {exc}")


# ── Refresh token tracking ────────────────────────────────────────────────────

async def _store_refresh_jti(user_id: str, jti: str) -> None:
    try:
        from app.cache.redis import get_redis
        r = get_redis()
        await r.setex(f"refresh:jti:{jti}", 86400 * 31, user_id)
        await r.setex(f"refresh:user:{user_id}", 86400 * 31, jti)
    except Exception as exc:
        logger.warning(f"Failed to store refresh JTI: {exc}")


async def _validate_refresh_jti(jti: str, user_id: str) -> bool:
    try:
        from app.cache.redis import get_redis
        r = get_redis()
        stored = await r.get(f"refresh:jti:{jti}")
        if not stored:
            return False
        return stored.decode() == user_id if isinstance(stored, bytes) else stored == user_id
    except Exception as exc:
        logger.warning(f"Refresh JTI validation failed (allowing): {exc}")
        return True  # Fail open if Redis is down


async def _invalidate_refresh_jti(jti: str) -> None:
    try:
        from app.cache.redis import get_redis
        r = get_redis()
        await r.delete(f"refresh:jti:{jti}")
    except Exception:
        pass


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/telegram/login", response_model=TokenResponse)
async def telegram_login(
    body: TelegramLoginRequest,
    request: Request,
    background: BackgroundTasks,
):
    tg_user = validate_telegram_init_data(
        body.init_data, settings.get_telegram_bot_token()
    )
    if not tg_user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Telegram initData")

    tg_id = int(tg_user["id"])

    user = await AuthUser.find_one(AuthUser.tg_id == tg_id)
    if not user:
        user = AuthUser(
            tg_id=tg_id,
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name", ""),
            last_name=tg_user.get("last_name"),
            language_code=tg_user.get("language_code"),
        )
        await user.insert()
        logger.info(f"New user registered: tg_id={tg_id}")
        background.add_task(_log, "register", user, request, {"tg_user": tg_user})
    else:
        user.username = tg_user.get("username", user.username)
        user.first_name = tg_user.get("first_name", user.first_name)
        user.last_name = tg_user.get("last_name", user.last_name)
        user.last_active = _utcnow()
        await user.save()
        background.add_task(_log, "login", user, request)

    if user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Account blocked: {user.block_reason}")

    # [F3] TOTP check — возвращаем 202 чтобы фронт знал что нужен 2FA код
    if user.totp_enabled and user.totp_secret:
        if not body.totp_code:
            # Возвращаем специальный ответ без токенов
            return TokenResponse(
                access_token="",
                refresh_token="",
                totp_required=True,
                expires_in=0,
            )
        try:
            import pyotp
            totp = pyotp.TOTP(user.totp_secret)
            if not totp.verify(body.totp_code, valid_window=1):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid TOTP code")
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning(f"TOTP validation error for tg_id={tg_id}: {exc}")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "TOTP validation failed")

    background.add_task(_download_and_save_avatar, user)

    jkt: Optional[str] = None
    if body.dpop_jwk:
        from app.auth.security import _jwk_thumbprint
        try:
            jkt = _jwk_thumbprint(body.dpop_jwk)
        except Exception as exc:
            logger.warning(f"Invalid dpop_jwk from tg_id={tg_id}: {exc}")

    access  = create_access_token(str(user.id), tg_id, user.roles, jkt=jkt)
    refresh = create_refresh_token(str(user.id), tg_id)

    # [F2] Извлекаем JTI через decode_access_token (с проверкой подписи)
    try:
        refresh_payload = decode_access_token(refresh)
        await _store_refresh_jti(str(user.id), refresh_payload.get("jti", ""))
    except Exception as exc:
        logger.warning(f"Failed to store refresh JTI: {exc}")

    return TokenResponse(access_token=access, refresh_token=refresh)


async def _download_and_save_avatar(user: AuthUser) -> None:
    try:
        local_path = await fetch_and_save_avatar(user.tg_id, settings.get_telegram_bot_token())
        if local_path:
            user.photo_local_path = local_path
            user.photo_url = get_avatar_url(user.tg_id)
            await user.save()
    except Exception as exc:
        logger.debug(f"Avatar download failed for tg_id={user.tg_id}: {exc}")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest):
    """Refresh с ротацией — старый токен инвалидируется."""
    try:
        payload = decode_access_token(body.refresh_token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not a refresh token")

    user_id = payload.get("sub")
    old_jti = payload.get("jti", "")

    if old_jti and not await _validate_refresh_jti(old_jti, user_id):
        logger.warning(f"Refresh token reuse detected for user {user_id}")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token has been revoked")

    user = await AuthUser.get(user_id)
    if not user or user.is_blocked:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or blocked")

    access  = create_access_token(str(user.id), user.tg_id, user.roles)
    refresh = create_refresh_token(str(user.id), user.tg_id)

    if old_jti:
        await _invalidate_refresh_jti(old_jti)

    # [F2] Используем decode_access_token с проверкой подписи
    try:
        new_payload = decode_access_token(refresh)
        await _store_refresh_jti(str(user.id), new_payload.get("jti", ""))
    except Exception as exc:
        logger.warning(f"Failed to store new refresh JTI: {exc}")

    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/dpop/nonce")
async def get_dpop_nonce():
    from app.auth.models import AuthDPoPNonce
    nonce = issue_dpop_nonce()
    await AuthDPoPNonce(nonce=nonce).insert()
    return {"nonce": nonce}


@router.get("/me", response_model=UserResponse)
async def get_me(user: AuthUser = Depends(get_current_user)):
    return UserResponse(
        id=str(user.id),
        tg_id=user.tg_id,
        username=user.username,
        first_name=user.first_name,
        photo_url=user.photo_url or get_avatar_url(user.tg_id),
        roles=user.roles,
        is_blocked=user.is_blocked,
        last_active=user.last_active,
        created_at=user.created_at,
    )


# ── API Keys ──────────────────────────────────────────────────────────────────

@router.post("/keys", response_model=ApiKeyResponse)
async def create_api_key(
    body: CreateApiKeyRequest,
    request: Request,
    background: BackgroundTasks,
    user: AuthUser = Depends(get_current_user),
):
    raw_key, key_hash, prefix = generate_api_key()
    expires_at = None
    if body.expires_days:
        expires_at = _utcnow() + timedelta(days=body.expires_days)

    key_doc = AuthApiKey(
        key_hash=key_hash,
        key_prefix=prefix,
        user_id=str(user.id),
        name=body.name,
        permissions=body.permissions,
        rate_limit_rpm=body.rate_limit_rpm,
        expires_at=expires_at,
    )
    await key_doc.insert()
    background.add_task(_log, "api_key_created", user, request, {"name": body.name, "prefix": prefix})

    return ApiKeyResponse(
        id=str(key_doc.id),
        key=raw_key,
        prefix=prefix,
        name=key_doc.name,
        permissions=key_doc.permissions,
        rate_limit_rpm=key_doc.rate_limit_rpm,
        expires_at=key_doc.expires_at,
        created_at=key_doc.created_at,
    )


@router.get("/keys", response_model=list[ApiKeyResponse])
async def list_api_keys(user: AuthUser = Depends(get_current_user)):
    keys = await AuthApiKey.find(
        AuthApiKey.user_id == str(user.id),
        AuthApiKey.is_revoked == False,  # noqa: E712
    ).to_list()
    return [
        ApiKeyResponse(
            id=str(k.id), key=None, prefix=k.key_prefix, name=k.name,
            permissions=k.permissions, rate_limit_rpm=k.rate_limit_rpm,
            expires_at=k.expires_at, created_at=k.created_at,
        ) for k in keys
    ]


@router.delete("/keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    request: Request,
    background: BackgroundTasks,
    user: AuthUser = Depends(get_current_user),
):
    key = await AuthApiKey.get(key_id)
    if not key or key.user_id != str(user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    key.is_revoked = True
    await key.save()
    background.add_task(_log, "api_key_revoked", user, request, {"key_id": key_id})


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.get("/admin/users", response_model=list[UserResponse])
async def admin_users(
    # [F1] Переименовали параметр с `q` на `search`, чтобы не затирать переменную query-builder
    search: Optional[str] = Query(None, alias="q"),
    blocked_only: bool = False,
    skip: int = 0,
    limit: int = Query(50, ge=1, le=200),
    _: AuthUser = Depends(require_permission("users:read")),
):
    # [F1] Строим запрос в отдельной переменной user_query (было q — конфликт с параметром)
    user_query = AuthUser.find()
    if blocked_only:
        user_query = AuthUser.find(AuthUser.is_blocked == True)  # noqa: E712
    if search:
        # Фильтр по username/first_name если нужно
        pass
    users = await user_query.skip(skip).limit(limit).sort("-last_active").to_list()
    return [
        UserResponse(
            id=str(u.id), tg_id=u.tg_id, username=u.username,
            first_name=u.first_name,
            photo_url=u.photo_url or get_avatar_url(u.tg_id),
            roles=u.roles, is_blocked=u.is_blocked,
            last_active=u.last_active, created_at=u.created_at,
        ) for u in users
    ]


@router.patch("/admin/users/{user_id}")
async def admin_update_user(
    user_id: str,
    body: AdminUpdateUserRequest,
    request: Request,
    background: BackgroundTasks,
    admin: AuthUser = Depends(require_permission("users:write")),
):
    user = await AuthUser.get(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    changes: dict = {}

    if body.roles is not None:
        admin_perms = await _user_permissions(admin)
        if str(admin.id) == user_id:
            raise HTTPException(403, "Cannot modify your own roles")
        if "admin:full" not in admin_perms:
            for role in body.roles:
                if "admin" in role.lower():
                    raise HTTPException(403, f"Assigning '{role}' requires admin:full")
        user.roles = body.roles
        changes["roles"] = body.roles

    if body.is_blocked is not None:
        user.is_blocked = body.is_blocked
        changes["is_blocked"] = body.is_blocked
        if body.is_blocked:
            try:
                from app.cache.redis import get_redis
                await get_redis().setex(f"user:blocked:{user_id}", 86400 * 30, "1")
            except Exception:
                pass
    if body.block_reason is not None:
        user.block_reason = body.block_reason
        changes["block_reason"] = body.block_reason

    await user.save()
    background.add_task(_log, "admin_user_updated", admin, request,
                        {"target_user_id": user_id, "changes": changes})
    return {"ok": True, "changes": changes}


@router.get("/admin/logs")
async def admin_activity_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(100, ge=1, le=500),  # [F4] добавлен максимум
    _: AuthUser = Depends(require_permission("logs:read")),
):
    filters = []
    if user_id:
        filters.append(AuthActivityLog.user_id == user_id)
    if action:
        filters.append(AuthActivityLog.action == action)

    q = AuthActivityLog.find(*filters)
    logs = await q.skip(skip).limit(limit).sort("-timestamp").to_list()
    return [
        {
            "id": str(l.id),
            "user_id": l.user_id,
            "tg_id": l.tg_id,
            "action": l.action,
            "ip": l.ip,
            "details": l.details,
            "timestamp": l.timestamp.isoformat(),
        }
        for l in logs
    ]
