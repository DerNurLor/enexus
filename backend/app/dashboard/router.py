"""
Dashboard HTML pages. Single-page apps — all data loaded from /dashboard/api/*.
"""
from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.core.config import settings

router = APIRouter(prefix="/dashboard", tags=["dashboard-ui"])

_HERE    = Path(__file__).parent / "templates"
_NO_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma":        "no-cache",
}


def _html(name: str) -> HTMLResponse:
    content = (_HERE / name).read_text(encoding="utf-8")
    return HTMLResponse(content, headers=_NO_CACHE)


async def _bootstrap_token(secret_provided: str) -> tuple[str | None, str]:
    """Issue a bootstrap JWT. Returns (token, accent_color)."""
    if not settings.dashboard_secret:
        return None, "#7c6eff"

    val1 = secret_provided.get_secret_value() if hasattr(secret_provided, "get_secret_value") else secret_provided
    val2 = settings.dashboard_secret.get_secret_value() if hasattr(settings.dashboard_secret, "get_secret_value") else settings.dashboard_secret
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


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_panel(secret: str | None = Query(default=None)):
    content = (_HERE / "admin.html").read_text(encoding="utf-8")

    if secret:
        token, accent = await _bootstrap_token(secret)
        admin_path = settings.admin_path.strip("/")
        prefix = f"/{admin_path}" if admin_path else ""
        if token:
            inject = (
                f'<script>'
                f'window.__BOOTSTRAP_TOKEN__="{token}";'
                f'window.__ADMIN_PREFIX__="{prefix}";'
                f'window.__ACCENT_COLOR__="{accent}";'
                f'</script>'
            )
            content = content.replace("</head>", inject + "\n</head>", 1)
        else:
            inject = (
                f'<script>window.__ADMIN_PREFIX__="{prefix}";</script>'
                '<script>window.addEventListener("DOMContentLoaded",()=>{'
                'const e=document.getElementById("auth-err");'
                'if(e){e.textContent="Неверный секретный ключ или нет пользователей.";e.style.display="block"}'
                '});</script>'
            )
            content = content.replace("</head>", inject + "\n</head>", 1)

    return HTMLResponse(content, headers=_NO_CACHE)


@router.get("/me", response_class=HTMLResponse, include_in_schema=False)
async def user_panel():
    return _html("me.html")
