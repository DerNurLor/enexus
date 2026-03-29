"""
ecampus/sync_service.py

Сервис синхронизации данных с eCampus.

Изменения v2:
  - save_credentials принимает session_cookies
  - Добавлен task_handler для обработки задач из очереди
  - Сессия восстанавливается из БД без повторной авторизации
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional, Any

from beanie import Document
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from loguru import logger
from pydantic import Field


# ── Шифрование AES-256-GCM ───────────────────────────────────────────────────

def _get_key() -> bytes:
    key_hex = os.environ.get("ECAMPUS_ENCRYPTION_KEY", "")
    if not key_hex or len(key_hex) != 64:
        raise ValueError("ECAMPUS_ENCRYPTION_KEY не задан. Сгенерируй: python3 -c \"import secrets; print(secrets.token_hex(32))\"")
    return bytes.fromhex(key_hex)

def encrypt_credential(plaintext: str) -> str:
    import base64
    key = _get_key()
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt_credential(encrypted_b64: str) -> str:
    import base64
    key = _get_key()
    data = base64.b64decode(encrypted_b64)
    return AESGCM(key).decrypt(data[:12], data[12:], None).decode()


# ── Модель ────────────────────────────────────────────────────────────────────

class ECampusSyncRecord(Document):
    tg_id:               int
    login_enc:           str
    password_enc:        str
    enabled:             bool = True
    student_id:          Optional[int] = None
    last_sync:           Optional[datetime] = None
    sync_status:         str = "pending"
    error_msg:           Optional[str] = None
    session_cookies_json: Optional[str] = None

    courses:  list[dict] = Field(default_factory=list)
    grades:   dict[str, Any] = Field(default_factory=dict)
    files:    list[dict] = Field(default_factory=list)
    links:    list[dict] = Field(default_factory=list)

    class Settings:
        name = "ecampus_sync"

    def get_session_cookies(self) -> dict:
        if not self.session_cookies_json:
            return {}
        try:
            return json.loads(self.session_cookies_json)
        except Exception:
            return {}

    def set_session_cookies(self, cookies: dict) -> None:
        self.session_cookies_json = json.dumps(cookies)


# ── CRUD ──────────────────────────────────────────────────────────────────────

async def save_credentials(
    tg_id: int,
    login: str,
    password: str,
    session_cookies: dict | None = None,
) -> ECampusSyncRecord:
    login_enc    = encrypt_credential(login)
    password_enc = encrypt_credential(password)

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == tg_id)
    if record is None:
        record = ECampusSyncRecord(
            tg_id=tg_id,
            login_enc=login_enc,
            password_enc=password_enc,
            sync_status="pending",
        )
        if session_cookies:
            record.set_session_cookies(session_cookies)
        await record.insert()
    else:
        update: dict = {
            "login_enc":    login_enc,
            "password_enc": password_enc,
            "sync_status":  "pending",
            "error_msg":    None,
        }
        if session_cookies:
            update["session_cookies_json"] = json.dumps(session_cookies)
        await record.set(update)

    logger.info(f"Credentials saved for tg_id={tg_id}")
    return record


async def delete_credentials(tg_id: int) -> bool:
    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == tg_id)
    if record:
        await record.delete()
        return True
    return False


# ── Task handler для очереди ──────────────────────────────────────────────────

async def task_handler(task) -> dict:
    """
    Обработчик задач из ECampusQueue.
    Вызывается воркером для каждой задачи.
    """
    if task.task_type == "sync_all":
        return await _handle_sync_all(task)
    elif task.task_type == "fetch_course":
        return await _handle_fetch_course(task)
    else:
        logger.warning(f"Unknown task type: {task.task_type}")
        return {}


async def _handle_sync_all(task) -> dict:
    """Собирает все данные пользователя (LOW приоритет)."""
    tg_id = task.tg_id

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == tg_id)
    if not record:
        raise ValueError(f"Record not found for tg_id={tg_id}")

    await record.set({"sync_status": "running"})

    try:
        from app.ecampus.client import ECampusClient

        login    = decrypt_credential(record.login_enc)
        password = decrypt_credential(record.password_enc)
        cookies  = record.get_session_cookies()

        async with ECampusClient(login, password, captcha_api_key="", session_cookies=cookies) as client:
            # Проверяем сессию
            vm = await client.get_studies_viewmodel()

            # Собираем данные
            result = await _collect_all_data(client, record, vm)

        # Обновляем сессию и данные
        await record.set({
            "sync_status":           "ok",
            "last_sync":             datetime.now(timezone.utc),
            "error_msg":             None,
            "session_cookies_json":  json.dumps(client.get_cookies()),
            "courses":               result["courses"],
            "grades":                result["grades"],
            "files":                 result["files"],
            "links":                 result["links"],
        })

        logger.info(f"Sync OK for tg_id={tg_id}: {len(result['courses'])} courses")
        return result

    except Exception as e:
        import traceback; logger.error(f"Sync failed for tg_id={tg_id}: {e}\n{traceback.format_exc()}")
        await record.set({"sync_status": "error", "error_msg": str(e)[:500]})
        raise


async def _handle_fetch_course(task) -> dict:
    """Получает данные одного курса (HIGH приоритет)."""
    tg_id      = task.tg_id
    course_url = task.payload.get("course_url", "")

    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == tg_id)
    if not record:
        raise ValueError(f"Record not found for tg_id={tg_id}")

    from app.ecampus.client import ECampusClient
    login    = decrypt_credential(record.login_enc)
    password = decrypt_credential(record.password_enc)
    cookies  = record.get_session_cookies()

    async with ECampusClient(login, password, captcha_api_key="", session_cookies=cookies) as client:
        details = await client.get_grades(course_url)
        # Обновляем сессию
        await record.set({"session_cookies_json": json.dumps(client.get_cookies())})
        return details


async def _collect_all_data(client, record: ECampusSyncRecord, viewmodel: dict) -> dict:
    """Собирает все доступные данные студента."""
    all_courses, all_grades, all_files, all_links = [], {}, [], []

    # Извлекаем данные из viewModel
    specialities = viewmodel.get("specialities", [])
    
    # student_id находится в specialities[0].Id
    student_id = record.student_id
    if specialities:
        student_id = specialities[0].get("Id") or record.student_id
    if not student_id:
        student_id = viewmodel.get("studentId") or viewmodel.get("StudentId") or viewmodel.get("Kod_cart")

    # Термины из specialities[0].AcademicYears[N].Terms — все учебные годы
    terms = viewmodel.get("terms", viewmodel.get("Terms", []))
    if not terms and specialities:
        for ay in specialities[0].get("AcademicYears", []):
            for term in ay.get("Terms", []):
                # Добавляем название курса в термин
                term["_year_name"] = ay.get("Name", "")
                terms.append(term)

    if not student_id:
        logger.warning("student_id not found in viewModel")
        return {"courses": [], "grades": {}, "files": [], "links": []}

    if record.student_id != student_id:
        await record.set({"student_id": student_id})

    for term in terms:  # все семестры
        term_id = term.get("id") or term.get("Id") or term.get("termId")
        if not term_id:
            continue
        try:
            courses = await client.get_courses(student_id, term_id)
            for course in courses:
                course["term_id"]   = term_id
                course["term_name"] = f"{term.get("_year_name", "")} {term.get("Name", term.get("name", ""))}".strip()
                course["lessons"] = {}
                for lt in course.get("LessonTypes", []):
                    lt_id = lt.get("Id")
                    if lt_id:
                        for attempt in range(3):
                            try:
                                lessons = await client.get_lessons(lt_id, student_id)
                                if lessons:
                                    course["lessons"][lt.get("Name", str(lt_id))] = lessons
                                break
                            except Exception as e:
                                if "ReadTimeout" in str(type(e).__name__) and attempt < 2:
                                    logger.warning(f"GetLessons timeout lt_id={lt_id}, retry {attempt+1}/3")
                                    import asyncio as _asyncio
                                    await _asyncio.sleep(5 * (attempt + 1))
                                else:
                                    logger.warning(f"GetLessons failed lt_id={lt_id}: {e.__class__.__name__}: {e}")
                                    break
                all_courses.append(course)
        except Exception as e:
            logger.warning(f"Term {term_id} failed: {e}")

    # Дедупликация файлов
    seen, unique_files = set(), []
    for f in all_files:
        if f["url"] not in seen:
            seen.add(f["url"])
            unique_files.append(f)

    return {"courses": all_courses, "grades": all_grades, "files": unique_files, "links": all_links}


async def sync_all_users() -> dict:
    """Ежедневный запуск синхронизации для всех пользователей через очередь."""
    from app.ecampus.queue import get_queue, ECampusTask, Priority
    import asyncio

    records = await ECampusSyncRecord.find(ECampusSyncRecord.enabled == True).to_list()  # noqa
    queue   = get_queue()
    count   = 0

    for record in records:
        task = ECampusTask(
            task_type="sync_all",
            tg_id=record.tg_id,
            priority=Priority.LOW,
            payload={},
        )
        await queue.enqueue(task)
        count += 1
        await asyncio.sleep(1)  # небольшая пауза между постановкой задач

    logger.info(f"Enqueued {count} daily sync tasks")
    return {"enqueued": count}
