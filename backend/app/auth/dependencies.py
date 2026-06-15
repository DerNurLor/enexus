from __future__ import annotations

import secrets
import time
from typing import Optional

import jwt as _jwt
from fastapi import Depends, Header, HTTPException, Request, status
from loguru import logger

from app.auth.models import AuthApiKey, AuthUser
from app.auth.security import decode_access_token, verify_api_key, validate_dpop_proof
from app.cache.redis import get_redis
from app.core.config import settings

# ── Role cache (in-memory, refreshed every 60s) ───────────────────────────────

_role_cache: dict[str, list[str]] = {}
_role_cache_ts: float = 0.0


async def _get_role_permissions(role_name: str) -> list[str]:
    global _role_cache, _role_cache_ts
    now = time.monotonic()
    if now - _role_cache_ts > 60:
        from app.auth.models import AuthRole
        try:
            roles = await AuthRole.find_all().to_list()
            _role_cache = {r.name: r.permissions for r in roles}
            _role_cache_ts = now
        except Exception as exc:
            logger.warning(f"Role cache refresh failed: {exc}")
    return _role_cache.get(role_name, [])


async def _user_permissions(user: AuthUser) -> set[str]:
    perms: set[str] = set()
    for role in user.roles:
        perms.update(await _get_role_permissions(role))
    if user.extra_permissions:
        perms.update(user.extra_permissions)
    return perms


# ── Request ID middleware ─────────────────────────────────────────────────────

class RequestIDMiddleware:
    """Injects X-Request-ID into every request for log correlation."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope)
            request_id = request.headers.get("X-Request-ID") or secrets.token_hex(8)
            scope.setdefault("state", {})
            scope["state"]["request_id"] = request_id

            async def send_with_header(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"x-request-id", request_id.encode()))
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_with_header)
        else:
            await self.app(scope, receive, send)


# ── Core auth resolver ────────────────────────────────────────────────────────

async def _resolve_bearer(token: str, request: Request) -> AuthUser:
    """Validate a Bearer JWT access token."""
    try:
        payload = decode_access_token(token)
    except _jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except _jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}")

    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not an access token")

    # DPoP binding check
    jkt = payload.get("cnf", {}).get("jkt")
    if jkt:
        dpop_proof = request.headers.get("DPoP")
        if not dpop_proof:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "DPoP proof required for this token",
                headers={"WWW-Authenticate": 'DPoP error="use_dpop_nonce"'},
            )
        method = request.method
        url = str(request.url).split("?")[0]

        ok, err, proof_jkt = validate_dpop_proof(
            dpop_proof, method, url, expected_jkt=jkt
        )
        if not ok:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"DPoP validation failed: {err}")

        # [S1] Extract JTI from the validated proof payload (not raw re-parse)
        try:
            import json as _json, base64
            body_b64 = dpop_proof.split(".")[1]
            decoded_body = _json.loads(base64.urlsafe_b64decode(body_b64 + "=" * (-len(body_b64) % 4)))
            jti = decoded_body.get("jti", "")
        except Exception:
            jti = ""

        if jti:
            r = get_redis()
            replay_key = f"dpop:jti:{jti}"
            try:
                if await r.exists(replay_key):
                    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "DPoP proof replayed")
                await r.setex(replay_key, 120, "1")
            except HTTPException:
                raise
            except Exception as exc:
                logger.warning(f"DPoP replay check failed (non-blocking): {exc}")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token: missing sub")

    # [S2] Fast blocked check via Redis
    try:
        r = get_redis()
        if await r.exists(f"user:blocked:{user_id}"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account blocked")
    except HTTPException:
        raise
    except Exception:
        pass  # Redis down — fall through to DB check

    user = await AuthUser.get(user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    if user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Account blocked: {user.block_reason}")

    # Per-user rate limiting
    from app.core.ratelimit import check_rate_limit, _get_user_rpm, _bucket
    rpm = await _get_user_rpm(user.roles)
    rl_key = f"rl:user:{user.id}:{_bucket()}"
    await check_rate_limit(rl_key, rpm)

    # Update last_active (fire and forget)
    from datetime import datetime, timezone
    user.last_active = datetime.now(timezone.utc)
    try:
        await user.save()
    except Exception:
        pass  # Non-critical — don't fail request

    return user


async def _resolve_api_key(raw_key: str, request: Request) -> AuthUser:
    """Validate an API key and enforce per-key rate limiting."""
    if not raw_key.startswith("ncfu_"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key format")

    prefix = raw_key[:12]
    candidates = await AuthApiKey.find(
        AuthApiKey.key_prefix == prefix,
        AuthApiKey.is_revoked == False,  # noqa: E712
    ).to_list()

    if not candidates:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API key not found")

    matched: AuthApiKey | None = None
    for candidate in candidates:
        if verify_api_key(raw_key, candidate.key_hash):
            matched = candidate
            break

    if not matched:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")

    from datetime import datetime, timezone
    if matched.expires_at and matched.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API key expired")

    # Per-key rate limiting
    r = get_redis()
    try:
        rl_key = f"apikey:rl:{matched.id}"
        count = await r.incr(rl_key)
        if count == 1:
            await r.expire(rl_key, 60)
        if count > matched.rate_limit_rpm:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Rate limit exceeded ({matched.rate_limit_rpm} rpm)",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"API key rate limit check failed: {exc}")

    user = await AuthUser.get(matched.user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User for this API key not found")
    if user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Account blocked: {user.block_reason}")

    # Update last_used
    matched.last_used_at = datetime.now(timezone.utc)
    matched.use_count = (matched.use_count or 0) + 1
    try:
        await matched.save()
    except Exception:
        pass

    return user


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> AuthUser:
    """
    Core dependency — extract user from:
    1. Authorization: Bearer <jwt>
    2. Authorization: ApiKey <key>
    3. X-API-Key: <key>
    """
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        return await _resolve_api_key(api_key_header, request)

    if not authorization:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, credential = authorization.partition(" ")
    if not credential:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed Authorization header")

    if scheme.lower() == "bearer":
        return await _resolve_bearer(credential, request)
    elif scheme.lower() == "apikey":
        return await _resolve_api_key(credential, request)
    else:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Unsupported auth scheme: {scheme}")


async def optional_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> Optional[AuthUser]:
    """Like get_current_user but returns None for unauthenticated requests."""
    try:
        return await get_current_user(request, authorization)
    except HTTPException:
        return None


# ── Permission-based dependencies ─────────────────────────────────────────────

def require_permission(permission: str):
    """FastAPI dependency factory — requires a specific permission string."""
    async def dep(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        perms = await _user_permissions(user)
        if permission not in perms and "admin:full" not in perms:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Permission '{permission}' required",
            )
        return user
    dep.__name__ = f"require_{permission.replace(':', '_')}"
    return dep


def require_any_role(*roles: str):
    """FastAPI dependency factory — requires any one of the specified roles."""
    async def dep(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not any(r in user.roles for r in roles):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"One of roles {roles} required",
            )
        return user
    dep.__name__ = f"require_role_{'_or_'.join(roles)}"
    return dep


def require_admin():
    """Shortcut: require admin:full permission."""
    return require_permission("admin:full")
