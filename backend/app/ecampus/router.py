"""
ecampus/router.py

API эндпоинты для eCampus интеграции.

Поток авторизации:
  1. GET  /api/ecampus/captcha          → возвращает base64 картинку капчи
  2. POST /api/ecampus/connect          → логин + пароль + captcha_code → авторизация
  3. GET  /api/ecampus/status           → статус синхронизации
  4. GET  /api/ecampus/data             → все данные
  5. GET  /api/ecampus/course/{id}      → данные конкретного курса (HIGH приоритет)
  6. POST /api/ecampus/sync             → запустить синхронизацию вручную
  7. DELETE /api/ecampus/disconnect     → удалить учётные данные

Приоритеты:
  - /course/{id}  → HIGH (пользователь открыл прямо сейчас)
  - /sync manual  → HIGH
  - фоновый сбор  → LOW
"""
from __future__ import annotations

import base64
import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

from app.auth.dependencies import get_current_user
from app.ecampus.captcha_solver import solve_math_captcha
from app.auth.models import AuthUser

router = APIRouter(prefix="/ecampus", tags=["ecampus"])


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
    Получает картинку капчи с eCampus и возвращает:
    - base64 изображение для отображения на сайте
    - captcha_cookie для последующей отправки формы (хранится в Redis)
    """
    import httpx
    from app.cache.redis import get_redis

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://ecampus.ncfu.ru/account/login",
    }

    try:
        async with httpx.AsyncClient(headers=headers, timeout=15, follow_redirects=True) as client:
            # Сначала получаем страницу входа — нужен CSRF токен
            login_resp = await client.get("https://ecampus.ncfu.ru/account/login")
            csrf_cookies = dict(client.cookies)

            # Получаем капчу
            captcha_resp = await client.get("https://ecampus.ncfu.ru/Captcha/Captcha")
            captcha_cookies = dict(client.cookies)

        # Сохраняем cookies в Redis привязанные к пользователю (TTL 10 минут)
        r = get_redis()
        session_data = json.dumps({
            "csrf_cookies":    csrf_cookies,
            "captcha_cookies": captcha_cookies,
        })
        await r.setex(f"ecampus:captcha_session:{current_user.tg_id}", 600, session_data)

        # Возвращаем base64 картинку
        img_b64 = base64.b64encode(captcha_resp.content).decode()
        return {
            "image": f"data:image/png;base64,{img_b64}",
            "expires_in": 600,
        }

    except Exception as e:
        logger.error(f"Failed to get captcha: {e}")
        raise HTTPException(status_code=503, detail=f"Не удалось получить капчу: {e}")


# ── Подключить аккаунт eCampus ────────────────────────────────────────────────


@router.get("/captcha/solve")
async def solve_captcha_auto(current_user: AuthUser = Depends(get_current_user)):
    """
    Получает картинку капчи с eCampus и решает её через 2captcha.
    Возвращает { answer, captcha_cookie } для использования при connect.
    """
    from app.core.config import settings
    import httpx, base64

    api_key = getattr(settings, "twocaptcha_api_key", "") or ""
    if not api_key:
        raise HTTPException(status_code=503, detail="2captcha API key не настроен.")

    ecampus_base = "https://ecampus.ncfu.ru"

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        # Получаем страницу логина для csrf + captcha cookie
        login_page = await client.get(f"{ecampus_base}/account/login")
        csrf_token = ""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(login_page.text, "html.parser")
        csrf_el = soup.find("input", {"name": "__RequestVerificationToken"})
        if csrf_el:
            csrf_token = csrf_el.get("value", "")

        # Получаем картинку капчи
        captcha_resp = await client.get(f"{ecampus_base}/Captcha/Captcha")
        if not captcha_resp.is_success:
            raise HTTPException(status_code=502, detail="Не удалось получить капчу с eCampus.")

        image_bytes = captcha_resp.content
        # Сохраняем captcha cookie
        captcha_cookie = dict(client.cookies).get("captcha", "")

    # Решаем через 2captcha
    answer = await solve_math_captcha(image_bytes, api_key)
    if not answer:
        raise HTTPException(status_code=502, detail="Не удалось решить капчу. Попробуйте вручную.")

    return {
        "answer":         answer,
        "captcha_cookie": captcha_cookie,
        "csrf_token":     csrf_token,
    }

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
    from app.ecampus.sync_service import save_credentials, ECampusSyncRecord
    from app.ecampus.client import ECampusClient, ECampusAuthError
    import httpx
    from bs4 import BeautifulSoup

    r = get_redis()

    from app.core.config import settings
    _2captcha_key = getattr(settings, "twocaptcha_api_key", "") or ""

    # Авторизуемся на eCampus
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            follow_redirects=True,
            timeout=60,
        ) as client:

            # Получаем CSRF токен и captcha cookie
            login_page = await client.get("https://ecampus.ncfu.ru/account/login")
            soup = BeautifulSoup(login_page.text, "html.parser")
            token_el = soup.find("input", {"name": "__RequestVerificationToken"})
            if not token_el:
                raise HTTPException(status_code=503, detail="Не удалось получить CSRF токен")
            csrf_token = token_el.get("value", "")

            # Получаем капчу
            captcha_resp = await client.get("https://ecampus.ncfu.ru/Captcha/Captcha")

            if body.auto_captcha and _2captcha_key:
                # Решаем через 2captcha
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

            # Отправляем форму входа
            resp = await client.post(
                "https://ecampus.ncfu.ru/account/login?returnUrl=%2Faccount",
                data={
                    "Login":    body.login,
                    "Password": body.password,
                    "Code":     captcha_code,
                    "RememberMe": "true",
                    "__RequestVerificationToken": csrf_token,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://ecampus.ncfu.ru/account/login",
                    "Origin": "https://ecampus.ncfu.ru",
                },
            )

            # Проверяем успешность
            if "account/login" in str(resp.url) or "validation-summary-errors" in resp.text:
                soup2 = BeautifulSoup(resp.text, "html.parser")
                err_el = soup2.select_one(".validation-summary-errors ul li")
                err_msg = err_el.text.strip() if err_el else "Неверный логин, пароль или капча"
                raise HTTPException(status_code=401, detail=err_msg)

            # Сохраняем сессию
            session_cookies = dict(client.cookies)

    except HTTPException:
        raise
    except Exception as e:
        import traceback; logger.error(f"eCampus auth failed for tg_id={current_user.tg_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=503, detail=f"Ошибка авторизации: {e}")

    # Сохраняем зашифрованные учётные данные и сессию
    record = await save_credentials(
        tg_id=current_user.tg_id,
        login=body.login,
        password=body.password,
        session_cookies=session_cookies,
    )

    # Удаляем временную сессию капчи
    await r.delete(f"ecampus:captcha_session:{current_user.tg_id}")

    # Лёгкий запрос: получаем группу из viewModel и сразу пишем в профиль
    background_tasks.add_task(_quick_fetch_group, current_user.tg_id, session_cookies)

    # Запускаем фоновый сбор данных (LOW приоритет)
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


# ── Получить данные конкретного курса (HIGH приоритет) ────────────────────────

@router.get("/course/{course_id}")
async def get_course_data(
    course_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Возвращает данные конкретного курса.
    Если данные устарели — запускает HIGH приоритет задачу обновления и ждёт.
    """
    from app.ecampus.sync_service import ECampusSyncRecord
    from app.ecampus.queue import get_queue, ECampusTask, Priority

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record:
        raise HTTPException(status_code=404, detail="Подключите eCampus в настройках.")

    # Ищем курс в кэшированных данных
    course = next((c for c in record.courses if str(c.get("id", "")) == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Курс не найден.")

    course_url = course.get("url") or course.get("Url")
    if not course_url:
        return {"course": course, "grades": [], "files": [], "links": []}

    # Запускаем HIGH приоритет задачу для свежих данных
    queue = get_queue()
    task = ECampusTask(
        task_type="fetch_course",
        tg_id=current_user.tg_id,
        priority=Priority.HIGH,
        payload={"course_url": course_url, "course_id": course_id},
    )
    task_id = await queue.enqueue(task)

    # Ждём результата (до 15 секунд)
    result = await queue.get_result(task_id, timeout=15.0)
    if result and result.get("ok"):
        return {"course": course, **result["data"]}

    # Если не дождались — возвращаем кэшированные данные
    cached_grades = record.grades.get(course.get("name", ""), [])
    return {
        "course": course,
        "grades": cached_grades,
        "files":  [f for f in record.files if course_id in f.get("url", "")],
        "links":  record.links,
        "cached": True,
    }


# ── Ручная синхронизация (умная) ─────────────────────────────────────────────

@router.post("/sync/course/{course_id}")
async def sync_single_course(
    course_id: int,
    term_id: int,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_user),
):
    """Обновление данных по конкретному предмету (HIGH приоритет)."""
    from app.ecampus.sync_service import ECampusSyncRecord
    from app.ecampus.queue import get_queue, ECampusTask, Priority

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record:
        raise HTTPException(404, "Подключите eCampus в настройках.")

    course = next(
        (c for c in record.courses if c.get("Id") == course_id and c.get("term_id") == term_id),
        None
    )
    if not course:
        raise HTTPException(404, "Курс не найден.")

    course_url = course.get("url") or course.get("Url")
    if not course_url:
        raise HTTPException(400, "URL курса недоступен.")

    queue = get_queue()
    task = ECampusTask(
        task_type="fetch_course",
        tg_id=current_user.tg_id,
        priority=Priority.HIGH,
        payload={"course_url": course_url, "course_id": str(course_id)},
    )
    task_id = await queue.enqueue(task)

    result = await queue.get_result(task_id, timeout=20.0)
    if result and result.get("ok"):
        return {"ok": True, "data": result["data"]}

    return {"ok": False, "detail": "Таймаут. Данные обновляются в фоне."}


@router.post("/sync")
async def manual_sync(
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Умная синхронизация:
      1. Проверяем что сессия ещё валидна (GET /studies → если JSON содержит
         'Доступ запрещен' — сессия протухла)
      2. Если сессия OK → запускаем фоновый сбор данных как раньше
      3. Если сессия протухла → пробуем тихо переавторизоваться через
         сохранённые логин/пароль + авто-капча (2captcha)
      4. Если авто-капча не настроена или не справилась →
         возвращаем session_expired=True, фронт покажет форму с капчей
    """
    from app.ecampus.sync_service import ECampusSyncRecord, decrypt_credential
    from app.core.config import settings

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record:
        raise HTTPException(status_code=404, detail="Подключите eCampus в настройках.")

    if record.sync_status == "running":
        raise HTTPException(status_code=409, detail="Синхронизация уже выполняется.")

    # ── Шаг 1: проверяем сессию ──────────────────────────────────────────────
    session_ok = await _check_session(record)

    if session_ok:
        background_tasks.add_task(_background_sync, current_user.tg_id)
        return {"ok": True, "message": "Синхронизация запущена."}

    # ── Шаг 2: сессия протухла — пробуем тихо переавторизоваться ─────────────
    _2captcha_key = getattr(settings, "twocaptcha_api_key", "") or ""
    if _2captcha_key:
        reauth_ok = await _silent_reauth(record, _2captcha_key)
        if reauth_ok:
            background_tasks.add_task(_background_sync, current_user.tg_id)
            return {"ok": True, "message": "Сессия обновлена, синхронизация запущена."}

    # ── Шаг 3: нужна капча от пользователя ───────────────────────────────────
    # Получаем свежую капчу и возвращаем её фронту
    try:
        captcha_data = await _fetch_fresh_captcha(current_user.tg_id)
        return {
            "ok": False,
            "session_expired": True,
            "captcha_image":   captcha_data["image"],
            "message":         "Сессия истекла. Введите капчу для повторного входа.",
        }
    except Exception as exc:
        logger.warning(f"Could not fetch captcha for reauth tg_id={current_user.tg_id}: {exc}")
        return {
            "ok": False,
            "session_expired": True,
            "message": "Сессия истекла. Пересоздайте подключение вручную.",
        }


@router.post("/reauth")
async def reauth_with_captcha(
    body: ConnectRequest,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Повторная авторизация с капчей от пользователя.
    Вызывается когда /sync вернул session_expired=True.
    Использует уже сохранённые логин/пароль — пользователь вводит только капчу.
    """
    from app.ecampus.sync_service import ECampusSyncRecord, decrypt_credential, save_credentials
    from app.core.config import settings
    import httpx
    from bs4 import BeautifulSoup

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record:
        raise HTTPException(status_code=404, detail="Подключите eCampus в настройках.")

    _2captcha_key = getattr(settings, "twocaptcha_api_key", "") or ""

    try:
        login    = decrypt_credential(record.login_enc)
        password = decrypt_credential(record.password_enc)
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка расшифровки учётных данных.")

    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
            timeout=60,
        ) as client:
            login_page = await client.get("https://ecampus.ncfu.ru/account/login")
            soup = BeautifulSoup(login_page.text, "html.parser")
            token_el = soup.find("input", {"name": "__RequestVerificationToken"})
            if not token_el:
                raise HTTPException(status_code=503, detail="Не удалось получить CSRF токен.")
            csrf_token = token_el.get("value", "")

            captcha_resp = await client.get("https://ecampus.ncfu.ru/Captcha/Captcha")

            if body.auto_captcha and _2captcha_key:
                captcha_code = await solve_math_captcha(captcha_resp.content, _2captcha_key)
                if not captcha_code:
                    # Не справились — отдаём капчу пользователю
                    img_b64 = base64.b64encode(captcha_resp.content).decode()
                    return {
                        "ok": False,
                        "session_expired": True,
                        "captcha_image": img_b64,
                        "message": "Не удалось решить капчу автоматически. Введите вручную.",
                    }
            else:
                captcha_code = body.captcha_code
                if not captcha_code:
                    raise HTTPException(status_code=400, detail="Введите код с картинки капчи.")

            resp = await client.post(
                "https://ecampus.ncfu.ru/account/login?returnUrl=%2Faccount",
                data={
                    "Login":    login,
                    "Password": password,
                    "Code":     captcha_code,
                    "RememberMe": "true",
                    "__RequestVerificationToken": csrf_token,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://ecampus.ncfu.ru/account/login",
                    "Origin":  "https://ecampus.ncfu.ru",
                },
            )

            if "account/login" in str(resp.url) or "validation-summary-errors" in resp.text:
                # Неверная капча или пароль сменился — возвращаем новую капчу
                captcha_resp2 = await client.get("https://ecampus.ncfu.ru/Captcha/Captcha")
                img_b64 = base64.b64encode(captcha_resp2.content).decode()
                return {
                    "ok": False,
                    "session_expired": True,
                    "captcha_image": img_b64,
                    "message": "Неверная капча. Попробуйте снова.",
                }

            session_cookies = dict(client.cookies)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ошибка авторизации: {e}")

    # Обновляем сессию
    await record.set({"session_cookies_json": json.dumps(session_cookies), "error_msg": None})

    background_tasks.add_task(_background_sync, current_user.tg_id)
    return {"ok": True, "message": "Сессия обновлена, синхронизация запущена."}


# ── Отключить eCampus ─────────────────────────────────────────────────────────

@router.get("/profile")
async def get_profile(current_user: AuthUser = Depends(get_current_user)):
    """
    Возвращает данные профиля студента (курс, специальность, форма обучения и т.д.).
    Данные берутся из кэша; обновляются раз в 3 дня фоновым планировщиком.
    """
    from app.ecampus.sync_service import ECampusSyncRecord
    from datetime import timezone as _tz

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record:
        raise HTTPException(status_code=404, detail="Подключите eCampus в настройках.")

    synced_at = record.profile_synced_at
    if synced_at and synced_at.tzinfo is None:
        synced_at = synced_at.replace(tzinfo=_tz.utc)

    return {
        "profile_details": record.profile_details or [],
        "profile_synced_at": synced_at.isoformat() if synced_at else None,
    }

@router.delete("/disconnect")
async def disconnect_ecampus(current_user: AuthUser = Depends(get_current_user)):
    from app.ecampus.sync_service import delete_credentials

    deleted = await delete_credentials(current_user.tg_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Учётные данные не найдены.")
    return {"ok": True}


# ── Фоновые задачи ────────────────────────────────────────────────────────────


async def _check_session(record) -> bool:
    """
    Проверяет валидность сохранённой сессии.
    eCampus возвращает {"message":"Доступ запрещен"} или редирект на /login
    когда сессия истекла.
    """
    import httpx
    cookies = record.get_session_cookies()
    if not cookies:
        return False
    try:
        async with httpx.AsyncClient(
            cookies=cookies,
            headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"},
            follow_redirects=False,
            timeout=15,
        ) as client:
            resp = await client.get("https://ecampus.ncfu.ru/studies")
            # Редирект на логин = сессия протухла
            if resp.status_code in (301, 302, 303):
                return False
            # JSON с запретом
            if resp.status_code == 403:
                return False
            try:
                data = resp.json()
                if "Доступ запрещен" in str(data.get("message", "")):
                    return False
            except Exception:
                pass
            # Если страница содержит форму логина — тоже протухло
            if "account/login" in str(resp.url) or "Войти в систему" in resp.text:
                return False
            return resp.status_code == 200
    except Exception as exc:
        logger.warning(f"Session check failed: {exc}")
        return False


async def _silent_reauth(record, captcha_api_key: str) -> bool:
    """
    Тихая переавторизация через сохранённые логин/пароль + авто-капча.
    Возвращает True если успешно, обновляет session_cookies в записи.
    """
    from app.ecampus.sync_service import decrypt_credential
    import httpx
    from bs4 import BeautifulSoup

    try:
        login    = decrypt_credential(record.login_enc)
        password = decrypt_credential(record.password_enc)
    except Exception:
        return False

    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
            timeout=60,
        ) as client:
            login_page = await client.get("https://ecampus.ncfu.ru/account/login")
            soup = BeautifulSoup(login_page.text, "html.parser")
            token_el = soup.find("input", {"name": "__RequestVerificationToken"})
            if not token_el:
                return False
            csrf_token = token_el.get("value", "")

            captcha_resp = await client.get("https://ecampus.ncfu.ru/Captcha/Captcha")
            captcha_code = await solve_math_captcha(captcha_resp.content, captcha_api_key)
            if not captcha_code:
                return False

            resp = await client.post(
                "https://ecampus.ncfu.ru/account/login?returnUrl=%2Faccount",
                data={
                    "Login":    login,
                    "Password": password,
                    "Code":     captcha_code,
                    "RememberMe": "true",
                    "__RequestVerificationToken": csrf_token,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://ecampus.ncfu.ru/account/login",
                    "Origin":  "https://ecampus.ncfu.ru",
                },
            )

            if "account/login" in str(resp.url) or "validation-summary-errors" in resp.text:
                return False

            await record.set({"session_cookies_json": json.dumps(dict(client.cookies)), "error_msg": None})
            logger.info(f"Silent reauth OK for tg_id={record.tg_id}")
            return True

    except Exception as exc:
        logger.warning(f"Silent reauth failed for tg_id={record.tg_id}: {exc}")
        return False


async def _fetch_fresh_captcha(tg_id: int) -> dict:
    """Получает свежую капчу и сохраняет captcha session в Redis."""
    import httpx

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
        timeout=20,
    ) as client:
        captcha_resp = await client.get("https://ecampus.ncfu.ru/Captcha/Captcha")
        captcha_cookies = dict(client.cookies)

    from app.cache.redis import get_redis
    r = get_redis()
    session_data = json.dumps({"captcha_cookies": captcha_cookies, "captcha_image": None})
    await r.setex(f"ecampus:captcha_session:{tg_id}", 600, session_data)

    img_b64 = base64.b64encode(captcha_resp.content).decode()
    return {"image": img_b64}
    task = ECampusTask(
        task_type="sync_all",
        tg_id=tg_id,
        priority=Priority.LOW,
        payload={},
    )
    await queue.enqueue(task)
    logger.info(f"Background sync enqueued for tg_id={tg_id}")


@router.get("/course/{course_id}/lessons")
async def get_course_lessons(
    course_id: int,
    term_id: int,
    group_id: int | None = None,
    current_user: AuthUser = Depends(get_current_user),
):
    """Возвращает занятия курса, обогащённые аудиторией из расписания."""
    from app.ecampus.sync_service import ECampusSyncRecord
    from app.db.database import get_motor_db

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

    # Обогащаем аудиторией из расписания если она пустая
    if group_id:
        from app.models.lesson import LessonDoc
        import re
        course_name = course.get("Name", "")
        course_name_short = course_name[:15]
        # Загружаем расписание группы через Beanie
        schedule_lessons = await LessonDoc.find(
            LessonDoc.group_id == group_id,
        ).to_list()
        # Фильтруем по предмету
        schedule_lessons = [
            sl for sl in schedule_lessons
            if sl.subject and re.search(re.escape(course_name_short), sl.subject, re.IGNORECASE)
        ]
        # Строим индекс дата -> аудитория
        room_by_date: dict[str, str] = {}
        for sl in schedule_lessons:
            date_key = sl.date.strftime("%Y-%m-%d") if sl.date else ""
            room = sl.room_name or ""
            if room and room != "None":
                room_by_date[date_key] = room

        # Обогащаем занятия
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


@router.get("/file/{file_type}")
async def proxy_ecampus_file(
    file_type: str,
    kodCh: int,
    current_user: AuthUser = Depends(get_current_user),
):
    """Проксирует скачивание файла с eCampus через сессию пользователя."""
    from app.ecampus.sync_service import ECampusSyncRecord
    from app.ecampus.client import ECampusClient, ECAMPUS_BASE
    from app.ecampus.sync_service import decrypt_credential
    from fastapi.responses import StreamingResponse
    import httpx

    FILE_PATHS = {
        "lecture":     f"/program/FileLectureDownload?kodCh={kodCh}",
        "umk":         f"/program/FileUMKDownload?kodCh={kodCh}",
        "instruction": f"/program/FileInstructionDownload?kodCh={kodCh}",
        "program":     f"/program/DownloadForStudent?kodCh={kodCh}",
    }

    if file_type not in FILE_PATHS:
        raise HTTPException(status_code=400, detail="Неизвестный тип файла.")

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record or not record.session_cookies_json:
        raise HTTPException(status_code=401, detail="Нет сессии eCampus. Переподключитесь.")

    import json
    cookies = json.loads(record.session_cookies_json)
    url = f"{ECAMPUS_BASE}{FILE_PATHS[file_type]}"

    try:
        async with httpx.AsyncClient(cookies=cookies, follow_redirects=True, timeout=30) as client:
            resp = await client.get(url)
            if resp.status_code == 302 or "account/login" in str(resp.url):
                raise HTTPException(status_code=401, detail="Сессия eCampus истекла. Переподключитесь.")
            if not resp.is_success:
                raise HTTPException(status_code=404, detail="Файл не найден.")

            content_type = resp.headers.get("content-type", "application/octet-stream")
            content_disp = resp.headers.get("content-disposition", f'attachment; filename="{file_type}_{kodCh}.pdf"')

            return StreamingResponse(
                iter([resp.content]),
                media_type=content_type,
                headers={"Content-Disposition": content_disp},
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {e}")


@router.get("/file/{file_type}")
async def proxy_ecampus_file(
    file_type: str,
    kodCh: int,
    current_user: AuthUser = Depends(get_current_user),
):
    """Проксирует скачивание файла с eCampus через сессию пользователя."""
    from app.ecampus.sync_service import ECampusSyncRecord
    from app.ecampus.client import ECampusClient, ECAMPUS_BASE
    from app.ecampus.sync_service import decrypt_credential
    from fastapi.responses import StreamingResponse
    import httpx

    FILE_PATHS = {
        "lecture":     f"/program/FileLectureDownload?kodCh={kodCh}",
        "umk":         f"/program/FileUMKDownload?kodCh={kodCh}",
        "instruction": f"/program/FileInstructionDownload?kodCh={kodCh}",
        "program":     f"/program/DownloadForStudent?kodCh={kodCh}",
    }

    if file_type not in FILE_PATHS:
        raise HTTPException(status_code=400, detail="Неизвестный тип файла.")

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == current_user.tg_id)
    if not record or not record.session_cookies_json:
        raise HTTPException(status_code=401, detail="Нет сессии eCampus. Переподключитесь.")

    import json
    cookies = json.loads(record.session_cookies_json)
    url = f"{ECAMPUS_BASE}{FILE_PATHS[file_type]}"

    try:
        async with httpx.AsyncClient(cookies=cookies, follow_redirects=True, timeout=30) as client:
            resp = await client.get(url)
            if resp.status_code == 302 or "account/login" in str(resp.url):
                raise HTTPException(status_code=401, detail="Сессия eCampus истекла. Переподключитесь.")
            if not resp.is_success:
                raise HTTPException(status_code=404, detail="Файл не найден.")

            content_type = resp.headers.get("content-type", "application/octet-stream")
            content_disp = resp.headers.get("content-disposition", f'attachment; filename="{file_type}_{kodCh}.pdf"')

            return StreamingResponse(
                iter([resp.content]),
                media_type=content_type,
                headers={"Content-Disposition": content_disp},
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {e}")


@router.get("/course/{course_id}/materials")
async def get_course_materials(
    course_id: int,
    term_id: int,
    current_user: AuthUser = Depends(get_current_user),
):
    """Возвращает список доступных материалов для курса."""
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

    # УМК дисциплины — всегда доступен
    materials.append({
        "label": "УМК дисциплины",
        "url": "https://dspace.ncfu.ru/",
        "icon": "📚",
        "external": True,
        "color": "#10b981",
    })

    # Курс лекций
    if course.get("HasLectures"):
        materials.append({
            "label": "Курс лекций",
            "url": f"{BASE}/file/lecture?kodCh={course_id}",
            "icon": "📖",
            "external": False,
            "color": "#3b82f6",
        })

    # Методические указания
    if course.get("HasUMK"):
        materials.append({
            "label": "Метод. указания",
            "url": f"{BASE}/file/umk?kodCh={course_id}",
            "icon": "📋",
            "external": False,
            "color": "#8b5cf6",
        })

    # Инструкция
    if course.get("HasInstruction"):
        materials.append({
            "label": "Инструкция",
            "url": f"{BASE}/file/instruction?kodCh={course_id}",
            "icon": "📄",
            "external": False,
            "color": "#f59e0b",
        })

    # Рабочая программа (если locked=True — значит файл доступен)
    if course.get("locked"):
        materials.append({
            "label": "Рабочая программа",
            "url": f"{BASE}/file/program?kodCh={course_id}",
            "icon": "📑",
            "external": False,
            "color": "#ef4444",
        })

    # СЭО — всегда
    materials.append({
        "label": "СЭО",
        "url": "https://el.ncfu.ru/",
        "icon": "🖥",
        "external": True,
        "color": "#6b7280",
    })

    # eCampus — прямая ссылка
    materials.append({
        "label": "eCampus",
        "url": "https://ecampus.ncfu.ru/studies",
        "icon": "🔗",
        "external": True,
        "color": "#6b7280",
    })

    return {"materials": materials}


# ── Фоновые задачи ────────────────────────────────────────────────────────────

async def _background_sync(tg_id: int) -> None:
    """Запускает LOW приоритет синхронизацию всех данных."""
    from app.ecampus.queue import get_queue, ECampusTask, Priority
    queue = get_queue()
    task = ECampusTask(task_type="sync_all", tg_id=tg_id, priority=Priority.LOW, payload={})
    await queue.enqueue(task)


async def _quick_fetch_group(tg_id: int, session_cookies: dict) -> None:
    """
    Лёгкий одиночный запрос к eCampus сразу после connect:
    получает viewModel со /studies, вытаскивает GroupName из specialities[0],
    ищет группу в локальной БД и записывает profile_group_id / profile_group_name
    в miniapp_settings пользователя.

    Запускается как BackgroundTask — ошибки логируются, но не прерывают ответ.
    """
    import httpx
    from app.auth.models import AuthUser
    from app.models.group import Group

    try:
        async with httpx.AsyncClient(
            cookies=session_cookies,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
            follow_redirects=True,
            timeout=httpx.Timeout(connect=10, read=30, write=10, pool=5),
        ) as client:
            resp = await client.get("https://ecampus.ncfu.ru/studies")
            resp.raise_for_status()

        # Парсим viewModel из JS на странице
        import re, json as _json
        vm: dict = {}
        match = re.search(r'viewModel\s*=\s*(\{.+?\});', resp.text, re.DOTALL)
        if match:
            try:
                vm = _json.loads(match.group(1))
            except _json.JSONDecodeError:
                pass

        if not vm:
            logger.warning(f"_quick_fetch_group: empty viewModel for tg_id={tg_id}")
            return

        # Ищем GroupName в specialities[0]
        specialities = vm.get("specialities", [])
        if not specialities:
            logger.debug(f"_quick_fetch_group: no specialities in viewModel tg_id={tg_id}")
            return

        sp = specialities[0]
        # eCampus хранит имя группы в поле GroupName (или groupName)
        raw_group_name: str = (
            sp.get("GroupName")
            or sp.get("groupName")
            or sp.get("Group")
            or sp.get("group")
            or ""
        ).strip()

        if not raw_group_name:
            logger.debug(f"_quick_fetch_group: GroupName not found in specialities[0] tg_id={tg_id}, keys={list(sp.keys())}")
            return

        logger.info(f"_quick_fetch_group: found group '{raw_group_name}' for tg_id={tg_id}")

        # Ищем группу в локальной БД (case-insensitive)
        group_doc = await Group.find_one(
            {"name": {"$regex": f"^{re.escape(raw_group_name)}$", "$options": "i"}}
        )

        group_id: int | None = group_doc.group_id if group_doc else None
        group_name: str = group_doc.name if group_doc else raw_group_name

        # Обновляем miniapp_settings пользователя
        user = await AuthUser.find_one(AuthUser.tg_id == tg_id)
        if not user:
            logger.warning(f"_quick_fetch_group: AuthUser not found tg_id={tg_id}")
            return

        settings: dict = dict(user.miniapp_settings or {})

        # Не перезатираем уже выставленные пользователем настройки
        if settings.get("profile_group_id") or settings.get("profile_group_name"):
            logger.debug(
                f"_quick_fetch_group: profile_group already set for tg_id={tg_id}, skipping"
            )
            return

        settings["profile_group_id"]   = group_id
        settings["profile_group_name"] = group_name
        settings["profile_group_confirmed"] = True
        settings["profile_group_confirmed"] = True
        settings["profile_role"]       = settings.get("profile_role") or "student"

        user.miniapp_settings = settings
        await user.save()

        logger.info(
            f"_quick_fetch_group: saved profile_group='{group_name}' "
            f"(id={group_id}) for tg_id={tg_id}"
        )

    except Exception as exc:
        # Не роняем connect — просто логируем
        logger.warning(f"_quick_fetch_group failed for tg_id={tg_id}: {exc}")
