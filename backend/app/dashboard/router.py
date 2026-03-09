"""
backend/app/dashboard/router.py

Serves the React SPA (built with Vite) for all dashboard UI routes.
The SPA handles client-side routing; the server always returns index.html
for /dashboard/* HTML requests.

Bootstrap injection: when ?secret=<DASHBOARD_SECRET> is provided on /dashboard/admin,
a JWT token + config variables are injected into <head> so the React app can
auto-authenticate without a login screen.
"""
from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, FileResponse

from app.core.config import settings

router = APIRouter(prefix="/dashboard", tags=["dashboard-ui"])

# React SPA built output directory (populated by the Node.js build stage in Dockerfile)
_SPA_DIR = Path("/app/static/spa")
_INDEX   = _SPA_DIR / "index.html"

_NO_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma":        "no-cache",
}


def _spa_index(inject_script: str = "") -> HTMLResponse:
    """Read index.html and optionally inject a <script> block before </head>."""
    if not _INDEX.exists():
        return HTMLResponse(
            "<h1>Dashboard not built</h1>"
            "<p>Run <code>npm run build</code> inside <code>dashboard/react/</code> "
            "or rebuild the Docker image.</p>",
            status_code=503,
        )
    content = _INDEX.read_text(encoding="utf-8")
    if inject_script:
        content = content.replace("</head>", inject_script + "\n</head>", 1)
    return HTMLResponse(content, headers=_NO_CACHE)


async def _bootstrap_token(secret_provided: str) -> tuple[str | None, str]:
    """Validate DASHBOARD_SECRET and issue a short-lived bootstrap JWT.
    Returns (token | None, accent_color).
    """
    if not settings.dashboard_secret:
        return None, "#7c6eff"

    val1 = (
        secret_provided.get_secret_value()
        if hasattr(secret_provided, "get_secret_value")
        else secret_provided
    )
    val2 = (
        settings.dashboard_secret.get_secret_value()
        if hasattr(settings.dashboard_secret, "get_secret_value")
        else settings.dashboard_secret
    )
    if not secrets.compare_digest(val1, val2):
        return None, "#7c6eff"

    from app.auth.security import create_access_token
    from app.auth.models import AuthUser

    admin_user = await AuthUser.find_one({"roles": "admin"})
    if not admin_user:
        first = await AuthUser.find_one({})
        if first:
            if "admin" not in first.roles:
                first.roles = list(first.roles) + ["admin"]
                await first.save()
            admin_user = first

    if admin_user:
        token = create_access_token(str(admin_user.id), admin_user.tg_id, admin_user.roles)
        accent = getattr(admin_user, "accent_color", "#7c6eff") or "#7c6eff"
        return token, accent
    return None, "#7c6eff"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_panel(secret: str | None = Query(default=None)):
    """Main admin SPA entry point. Supports bootstrap auth via ?secret=."""
    admin_path = settings.admin_path.strip("/")
    prefix = f"/{admin_path}" if admin_path else ""

    if secret:
        token, accent = await _bootstrap_token(secret)
        if token:
            inject = (
                f"<script>"
                f'window.__BOOTSTRAP_TOKEN__="{token}";'
                f'window.__ADMIN_PREFIX__="{prefix}";'
                f'window.__ACCENT_COLOR__="{accent}";'
                f"</script>"
            )
        else:
            inject = (
                f'<script>window.__ADMIN_PREFIX__="{prefix}";</script>'
                "<script>window.addEventListener('DOMContentLoaded',()=>{"
                "const e=document.getElementById('auth-err');"
                "if(e){e.textContent='Неверный секретный ключ или нет пользователей.';"
                "e.style.display='block'}"
                "});</script>"
            )
        return _spa_index(inject)

    # No secret — inject only prefix (React app shows login form)
    inject = f'<script>window.__ADMIN_PREFIX__="{prefix}";</script>'
    return _spa_index(inject)


@router.get("/me", response_class=HTMLResponse, include_in_schema=False)
async def user_panel():
    """User profile SPA (same React app, different initial route)."""
    return _spa_index()


@router.get("/{path:path}", include_in_schema=False)
async def spa_fallback(path: str, request: Request):
    """
    Catch-all for client-side React Router routes under /dashboard/*.
    Static assets (JS/CSS/images) are served directly; everything else
    returns index.html so React Router can handle the route.
    """
    # Try serving a real static asset first
    asset = _SPA_DIR / path
    if asset.exists() and asset.is_file():
        return FileResponse(asset)

    # Fall back to SPA index for React Router navigation
    return _spa_index()
