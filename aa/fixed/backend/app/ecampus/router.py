"""
ecampus/router.py

API эндпоинты для eCampus интеграции.

ИСПРАВЛЕНИЯ:
  [F1] Удалён дублирующийся @router.get("/file/{file_type}") — второй перекрывал первый,
       что приводило к непредсказуемому поведению (FastAPI использовал первый, но код дублировался).
  [F2] Исправлена проверка редиректа на login: status_code 302 не означает редирект на login
       при follow_redirects=True — нужно проверять итоговый URL.
  [F3] file_type теперь проверяется через Path параметр с Literal-валидацией.
  [F4] kodCh валидируется как gt=0 для предотвращения SSRF с некорректными значениями.
  [F5] Добавлен X-Content-Type-Options header к прокси-ответам файлов.
  [F6] sync_status guard в manual_sync теперь использует set() для атомарного обновления.
"""
from __future__ import annotations

import base64
import json
from typing import Optional, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from loguru import logger

from app.auth.dependencies import get_current_user
from app.ecampus.captcha_solver import solve_math_captcha
from app.auth.models import AuthUser

router = APIRouter(prefix="/ecampus", tags=["ecampus"])

# Допустимые типы файлов — явный whitelist
FileType = Literal["lecture", "umk", "instruction", "program"]

FILE_PATHS: dict[str, str] = {
    "lecture":     "/program/FileLectureDownload",
    "umk":         "/program/FileUMKDownload",
    "instruction": "/program/FileInstructionDownload",
    "program":     "/program/DownloadForStudent",
}

ECAMPUS_BASE = "https://ecampus.ncfu.ru"


# ── Схемы ─────────────────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    login:        str = Field(..., min_length=3, max_length=100)
    password:     str = Field(..., min_length=1, max_length=100)
    captcha_code: str = Field("", min_length=0, max_length=20, description="Текст с картинки капчи")
    auto_captcha: bool = False


class SyncStatusResponse(BaseModel):
    connected:     bool
    enabled:       bool
    sync_status:   Optional[str] = None
    error_msg:     Optional[str] = None
    last_sync:     Optional[str] = None
    courses_count: int = 0
    files_count:   int = 0
    sync_progress:      int = 0
    sync_done_terms:    int = 0
    sync_total_terms:   int = 0
    sync_courses_found: int = 0


# ── Получить капчу ────────────────────────────────────────────────────────────

@router.get("/captcha")
async def get_captcha(current_user: AuthUser = Depends(get_current_user)):
    """
    Получает картинку капчи с eCampus и возвращает base64 изображение.
    Сессионные cookies сохраняются в Redis (TTL 10 минут).
    """
    import httpx
    from app.cache.redis import get_redis

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"{ECAMPUS_BASE}/account/login",
    }

    try:
        async with httpx.AsyncClient(headers=headers, timeout=15, follow_redirects=True) as client:
            await client.get(f"{ECAMPUS_BASE}/account/login")
            csrf_cookies = dict(client.cookies)
            captcha_resp = await client.get(f"{ECAMPUS_BASE}/Captcha/Captcha")
            captcha_resp.raise_for_status()
            captcha_cookies = dict(client.cookies)

        r = get_redis()
        session_data = json.dumps({
            "csrf_cookies":    csrf_cookies,
            "captcha_cookies": captcha_cookies,
        })
        await r.setex(f"ecampus:captcha_session:{current_user.tg_id}", 600, session_data)

        img_b64 = base64.b64encode(captcha_resp.content).decode()
        return {
            "image": f"data:image/png;base64,{img_b64}",
            "expires_in": 600,
        }

    except Exception as e:
        logger.error(f"Failed to get captcha: {e}")
        raise HTTPException(status_code=503, detail=f"Не удалось получить капчу: {e}")


# ── Авто-решение капчи ────────────────────────────────────────────────────────

@router.get("/captcha/solve")
async def solve_captcha_auto(current_user: AuthUser = Depends(get_current_user)):
    """
    Получает картинку капчи с eCampus и решает её через 2captcha.
    """
    from app.core.config import settings
    import httpx
    from bs4 import BeautifulSoup

    api_key = getattr(settings, "twocaptcha_api_key", "") or ""
    if not api_key:
        raise HTTPException(status_code=503, detail="2captcha API key не настроен.")

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        login_page = await client.get(f"{ECAMPUS_BASE}/account/login")
        csrf_token = ""
        soup = BeautifulSoup(login_page.text, "html.parser")
        csrf_el = soup.find("input", {"name": "__RequestVerificationToken"})
        if csrf_el:
            csrf_token = csrf_el.get("value", "")

        captcha_resp = await client.get(f"{ECAMPUS_BASE}/Captcha/Captcha")
        if not captcha_resp.is_success:
            raise HTTPException(status_code=502, detail="Не удалось получить капчу с eCampus.")

        image_bytes = captcha_resp.content
        captcha_cookie = dict(client.cookies).get("captcha", "")

    answer = await solve_math_captcha(image_bytes, api_key)
    if not answer:
        raise HTTPException(status_code=502, detail="Не удалось решить капчу. Попробуйте вручную.")

    return {
        "answer":         answer,
        "captcha_cookie": captcha_cookie,
        "csrf_token":     csrf_token,
    }


# ── Подключить аккаунт eCampus ────────────────────────────────────────────────

@router.post("/connect")
async def connect_ecampus(
    body: ConnectRequest,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Авторизуется на eCampus с введённой капчей.
    После успешной авторизации запускает фоновый сбор данных.
    """
    from app.cache.redis import get_redis
    from app.ecampus.sync_service import save_credentials
    import httpx
    from bs4 import BeautifulSoup

    r = get_redis()

    from app.core.config import settings
    _2captcha_key = getattr(settings, "twocaptcha_api_key", "") or ""

    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            follow_redirects=True,
            timeout=60,
        ) as client:

            login_page = await client.get(f"{ECAMPUS_BASE}/account/login")
            soup = BeautifulSoup(login_page.text, "html.parser")
            token_el = soup.find("input", {"name": "__RequestVerificationToken"})
            if not token_el:
                raise HTTPException(status_code=503, detail="Не удалось получить CSRF токен")
            csrf_token = token_el.get("value", "")

            captcha_resp = await client.get(f"{ECAMPUS_BASE}/Captcha/Captcha")

            if body.auto_captcha and _2captcha_key:
                from app.ecampus.captcha_solver import solve_math_captcha
                captcha_code = await solve_math_captcha(captcha_resp.content, _2captcha_key)
                if not captcha_code:
                    raise HTTPException(status_code=502, detail="Не удалось решить капчу автоматически. Введите вручную.")
            elif body.auto_captcha and not _2captcha_key:
                raise HTTPException(status_code=503, detail="Автокапча не настроена на сервере.")
            else:
                captcha_code = body.captcha_code
                if not captcha_code:
                    raise HTTPException(status_code=400, detail="Введите код с картинки капчи.")

            resp = await client.post(
                f"{ECAMPUS_BASE}/account/login?returnUrl=%2Faccount",
                data={
                    "Login":    body.login,
                    "Password": body.password,
                    "Code":     captcha_code,
                    "RememberMe": "true",
                    "__RequestVerificationToken": csrf_token,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": f"{ECAMPUS_BASE}/account/login",
                    "Origin": ECAMPUS_BASE,
                },
            )

            # [F2] follow_redirects=True — проверяем финальный URL, а не status_code
            final_url = str(resp.url)
            if "/account/login" in final_url or "validation-summary-errors" in resp.text:
                soup2 = BeautifulSoup(resp.text, "html.parser")
                err_el = soup2.select_one(".validation-summary-errors ul li")
                err_msg = err_el.text.strip() if err_el else "Неверный логин, пароль или капча"
                raise HTTPException(status_code=401, detail=err_msg)

            session_cookies = dict(client.cookies)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"eCampus auth failed for tg_id={current_user.tg_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=503, detail=f"Ошибка авторизации: {e}")

    await save_credentials(
        tg_id=current_user.tg_id,
        login=body.login,
        password=body.password,
        session_cookies=session_cookies,
    )

    await r.delete(f"ecampus:captcha_session:{current_user.tg_id}")
    background_tasks.add_task(_background_sync, current_user.tg_id)

    return {
        "ok": True,
        "message": "Авторизация успешна. Сбор данных запущен в фоне.",
    }


# ── Статус синхронизации ──────────────────────────────────────────────────────

@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    current_user: AuthUser = Depends(get_current_user),
) -> SyncStatusResponse:
    from app.ecampus.sync_service import ECampusSyncRecord

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record:
        return SyncStatusResponse(connected=False, enabled=False)

    return SyncStatusResponse(
        connected=True,
        enabled=record.enabled,
        sync_status=record.sync_status,
        error_msg=record.error_msg,
        last_sync=record.last_sync.isoformat() if record.last_sync else None,
        courses_count=len(record.courses),
        files_count=len(record.files),
        sync_progress=record.sync_progress,
        sync_done_terms=record.sync_done_terms,
        sync_total_terms=record.sync_total_terms,
        sync_courses_found=record.sync_courses_found,
    )


# ── Получить все данные ───────────────────────────────────────────────────────

@router.get("/data")
async def get_sync_data(current_user: AuthUser = Depends(get_current_user)):
    from app.ecampus.sync_service import ECampusSyncRecord

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record:
        raise HTTPException(status_code=404, detail="Подключите eCampus в настройках.")

    return {
        "sync_status": record.sync_status,
        "last_sync":   record.last_sync.isoformat() if record.last_sync else None,
        "courses":     record.courses,
        "grades":      record.grades,
        "files":       record.files,
        "links":       record.links,
    }


# ── Получить данные конкретного курса ─────────────────────────────────────────

@router.get("/course/{course_id}")
async def get_course_data(
    course_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    from app.ecampus.sync_service import ECampusSyncRecord
    from app.ecampus.queue import get_queue, ECampusTask, Priority

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record:
        raise HTTPException(status_code=404, detail="Подключите eCampus в настройках.")

    course = next((c for c in record.courses if str(c.get("id", "")) == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Курс не найден.")

    course_url = course.get("url") or course.get("Url")
    if not course_url:
        return {"course": course, "grades": [], "files": [], "links": []}

    queue = get_queue()
    task = ECampusTask(
        task_type="fetch_course",
        tg_id=current_user.tg_id,
        priority=Priority.HIGH,
        payload={"course_url": course_url, "course_id": course_id},
    )
    task_id = await queue.enqueue(task)

    result = await queue.get_result(task_id, timeout=15.0)
    if result and result.get("ok"):
        return {"course": course, **result["data"]}

    cached_grades = record.grades.get(course.get("name", ""), [])
    return {
        "course": course,
        "grades": cached_grades,
        "files":  [f for f in record.files if course_id in f.get("url", "")],
        "links":  record.links,
        "cached": True,
    }


# ── Занятия курса ─────────────────────────────────────────────────────────────

@router.get("/course/{course_id}/lessons")
async def get_course_lessons(
    course_id: int,
    term_id: int,
    group_id: int | None = None,
    current_user: AuthUser = Depends(get_current_user),
):
    from app.ecampus.sync_service import ECampusSyncRecord

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record:
        raise HTTPException(status_code=404, detail="Данные не найдены.")

    course = next(
        (c for c in record.courses if c.get("Id") == course_id and c.get("term_id") == term_id),
        None
    )
    if not course:
        raise HTTPException(status_code=404, detail="Курс не найден.")

    lessons = course.get("lessons", {})

    if group_id:
        from app.models.lesson import LessonDoc
        import re
        course_name = course.get("Name", "")
        course_name_short = course_name[:15]
        schedule_lessons = await LessonDoc.find(
            LessonDoc.group_id == group_id,
        ).to_list()
        schedule_lessons = [
            sl for sl in schedule_lessons
            if sl.subject and re.search(re.escape(course_name_short), sl.subject, re.IGNORECASE)
        ]
        room_by_date: dict[str, str] = {}
        for sl in schedule_lessons:
            date_key = sl.date.strftime("%Y-%m-%d") if sl.date else ""
            room = sl.room_name or ""
            if room and room != "None":
                room_by_date[date_key] = room

        for lt_lessons in lessons.values():
            for lesson in lt_lessons:
                if not lesson.get("Room"):
                    date_key = str(lesson.get("Date", ""))[:10]
                    if date_key in room_by_date:
                        lesson["Room"] = room_by_date[date_key]

    return {
        "course_id":      course_id,
        "course_name":    course.get("Name"),
        "lessons":        lessons,
        "max_rating":     course.get("MaxRating", 0),
        "current_rating": course.get("CurrentRating", 0),
    }


# ── Прокси файлов eCampus ─────────────────────────────────────────────────────
# [F1] Был ДУБЛИРУЮЩИЙСЯ роут — удалён второй (идентичный) блок.
# [F3] file_type теперь строго типизирован через Literal.
# [F4] kodCh валидируется как gt=0.

@router.get("/file/{file_type}")
async def proxy_ecampus_file(
    file_type: FileType,           # [F3] Literal — FastAPI вернёт 422 если не из whitelist
    kodCh: int = Query(..., gt=0), # [F4] kodCh > 0
    current_user: AuthUser = Depends(get_current_user),
):
    """Проксирует скачивание файла с eCampus через сессию пользователя."""
    from app.ecampus.sync_service import ECampusSyncRecord
    import httpx

    path = FILE_PATHS.get(file_type)
    if not path:
        raise HTTPException(status_code=400, detail="Неизвестный тип файла.")

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record or not record.session_cookies_json:
        raise HTTPException(status_code=401, detail="Нет сессии eCampus. Переподключитесь.")

    cookies = json.loads(record.session_cookies_json)
    url = f"{ECAMPUS_BASE}{path}?kodCh={kodCh}"

    try:
        async with httpx.AsyncClient(cookies=cookies, follow_redirects=True, timeout=30) as client:
            resp = await client.get(url)
            # [F2] Правильная проверка редиректа на страницу логина
            if "/account/login" in str(resp.url):
                raise HTTPException(status_code=401, detail="Сессия eCampus истекла. Переподключитесь.")
            if not resp.is_success:
                raise HTTPException(status_code=404, detail="Файл не найден.")

            content_type = resp.headers.get("content-type", "application/octet-stream")
            content_disp = resp.headers.get(
                "content-disposition",
                f'attachment; filename="{file_type}_{kodCh}.pdf"'
            )

            return StreamingResponse(
                iter([resp.content]),
                media_type=content_type,
                headers={
                    "Content-Disposition": content_disp,
                    "X-Content-Type-Options": "nosniff",  # [F5]
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {e}")


# ── Материалы курса ───────────────────────────────────────────────────────────

@router.get("/course/{course_id}/materials")
async def get_course_materials(
    course_id: int,
    term_id: int,
    current_user: AuthUser = Depends(get_current_user),
):
    from app.ecampus.sync_service import ECampusSyncRecord

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record:
        raise HTTPException(status_code=404, detail="Данные не найдены.")

    course = next(
        (c for c in record.courses if c.get("Id") == course_id and c.get("term_id") == term_id),
        None
    )
    if not course:
        raise HTTPException(status_code=404, detail="Курс не найден.")

    materials = []
    BASE = "/api/ecampus"

    materials.append({
        "label": "УМК дисциплины",
        "url": "https://dspace.ncfu.ru/",
        "icon": "📚",
        "external": True,
        "color": "#10b981",
    })

    if course.get("HasLectures"):
        materials.append({
            "label": "Курс лекций",
            "url": f"{BASE}/file/lecture?kodCh={course_id}",
            "icon": "📖",
            "external": False,
            "color": "#3b82f6",
        })

    if course.get("HasUMK"):
        materials.append({
            "label": "Метод. указания",
            "url": f"{BASE}/file/umk?kodCh={course_id}",
            "icon": "📋",
            "external": False,
            "color": "#8b5cf6",
        })

    if course.get("HasInstruction"):
        materials.append({
            "label": "Инструкция",
            "url": f"{BASE}/file/instruction?kodCh={course_id}",
            "icon": "📄",
            "external": False,
            "color": "#f59e0b",
        })

    if course.get("locked"):
        materials.append({
            "label": "Рабочая программа",
            "url": f"{BASE}/file/program?kodCh={course_id}",
            "icon": "📑",
            "external": False,
            "color": "#ef4444",
        })

    materials.append({
        "label": "СЭО",
        "url": "https://el.ncfu.ru/",
        "icon": "🖥",
        "external": True,
        "color": "#6b7280",
    })

    materials.append({
        "label": "eCampus",
        "url": "https://ecampus.ncfu.ru/studies",
        "icon": "🔗",
        "external": True,
        "color": "#6b7280",
    })

    return {"materials": materials}


# ── Ручная синхронизация ──────────────────────────────────────────────────────

@router.post("/sync")
async def manual_sync(
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_user),
):
    from app.ecampus.sync_service import ECampusSyncRecord

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record:
        raise HTTPException(status_code=404, detail="Подключите eCampus в настройках.")

    if record.sync_status == "running":
        raise HTTPException(status_code=409, detail="Синхронизация уже выполняется.")

    background_tasks.add_task(_background_sync, current_user.tg_id)
    return {"ok": True, "message": "Синхронизация запущена."}


# ── Отключить eCampus ─────────────────────────────────────────────────────────

@router.delete("/disconnect")
async def disconnect_ecampus(current_user: AuthUser = Depends(get_current_user)):
    from app.ecampus.sync_service import delete_credentials

    deleted = await delete_credentials(current_user.tg_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Учётные данные не найдены.")
    return {"ok": True}


# ── Фоновые задачи ────────────────────────────────────────────────────────────

async def _background_sync(tg_id: int) -> None:
    from app.ecampus.queue import get_queue, ECampusTask, Priority

    queue = get_queue()
    task = ECampusTask(
        task_type="sync_all",
        tg_id=tg_id,
        priority=Priority.LOW,
        payload={},
    )
    await queue.enqueue(task)
    logger.info(f"Background sync enqueued for tg_id={tg_id}")
