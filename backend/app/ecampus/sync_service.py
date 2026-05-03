"""
ecampus/sync_service.py

Сервис синхронизации данных с eCampus.

Изменения v2:
  - save_credentials принимает session_cookies
  - Добавлен task_handler для обработки задач из очереди
  - Сессия восстанавливается из БД без повторной авторизации
"""
from __future__ import annotations

import asyncio
import httpx
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
    sync_progress:       int = 0
    sync_done_terms:     int = 0
    sync_total_terms:    int = 0
    sync_loaded_term_ids: list = []  # term_id-ы уже загруженных семестров
    sync_courses_found:  int = 0
    error_msg:           Optional[str] = None
    retry_count:         int = 0          # сколько раз авто-retry после ошибки
    session_cookies_json: Optional[str] = None

    profile_details: list[dict] = Field(default_factory=list)
    profile_synced_at: Optional[datetime] = None
    courses:  list[dict] = Field(default_factory=list)
    grades:   dict[str, Any] = Field(default_factory=dict)
    files:    list[dict] = Field(default_factory=list)
    links:    list[dict] = Field(default_factory=list)
    zachetka: dict       = Field(default_factory=dict)   # /details/zachetka viewModel

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
    elif task.task_type == "sync_profile":
        return await _handle_sync_profile(task)
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

    await record.set({"sync_status": "running", "sync_progress": 0, "sync_done_terms": 0, "sync_courses_found": 0, "sync_loaded_term_ids": []})

    try:
        from app.ecampus.client import ECampusClient

        login    = decrypt_credential(record.login_enc)
        password = decrypt_credential(record.password_enc)
        cookies  = record.get_session_cookies()

        async with ECampusClient(login, password, captcha_api_key="", session_cookies=cookies) as client:
            # Проверяем сессию — retry при ReadTimeout
            vm = None
            for _attempt in range(3):
                try:
                    vm = await client.get_studies_viewmodel()
                    break
                except httpx.ReadTimeout:
                    if _attempt < 2:
                        logger.warning(f"get_studies_viewmodel ReadTimeout tg_id={tg_id}, retry {_attempt+1}/3")
                        await asyncio.sleep(10)
                    else:
                        raise
            if vm is None:
                raise RuntimeError("get_studies_viewmodel failed after 3 attempts")

            # Собираем данные
            result = await _collect_all_data(client, record, vm)

        # Обновляем сессию и данные
        await record.set({
            "sync_status":           "ok",
            "sync_progress":         100,
            "last_sync":             datetime.now(timezone.utc),
            "error_msg":             None,
            "retry_count":           0,   # сброс после успешной синхронизации
            "session_cookies_json":  json.dumps(client.get_cookies()),
            "courses":               result["courses"],
            "grades":                result["grades"],
            "files":                 result["files"],
            "links":                 result["links"],
        })
        # zachetka уже сохранена внутри _collect_all_data после получения

        logger.info(f"Sync OK for tg_id={tg_id}: {len(result['courses'])} courses")
        return result

    except Exception as e:
        import traceback; logger.error(f"Sync failed for tg_id={tg_id}: {e}\n{traceback.format_exc()}")
        await record.set({"sync_status": "error", "error_msg": str(e)[:500]})
        raise


async def _handle_sync_profile(task) -> dict:
    """Обновляет только профиль пользователя (быстро, без загрузки курсов)."""
    tg_id = task.tg_id
    record = await ECampusSyncRecord.find_one(ECampusSyncRecord.tg_id == tg_id)
    if not record:
        raise ValueError(f"Record not found for tg_id={tg_id}")

    from app.ecampus.client import ECampusClient
    login    = decrypt_credential(record.login_enc)
    password = decrypt_credential(record.password_enc)
    cookies  = record.get_session_cookies()

    async with ECampusClient(login, password, captcha_api_key="", session_cookies=cookies) as client:
        details = await client.get_details()
        await record.set({
            "profile_details":    details,
            "profile_synced_at":  datetime.now(timezone.utc),
            "session_cookies_json": json.dumps(client.get_cookies()),
        })

    logger.info(f"Profile sync OK for tg_id={tg_id}: {len(details)} entries")
    return {"profile_details": details}

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

    # Получаем профиль студента
    try:
        details = await client.get_details()
        if details:
            await record.set({
                "profile_details": details,
                "profile_synced_at": datetime.now(timezone.utc),
            })
            logger.info(f"Profile synced for tg_id={record.tg_id}: {len(details)} entries")
    except Exception as _e:
        logger.warning(f"Profile fetch failed for tg_id={record.tg_id}: {_e}")

    # Зачётная книжка — итоговые оценки за все семестры
    try:
        zachetka = await client.get_zachetka()
        if zachetka.get("education_details"):
            await record.set({"zachetka": zachetka})
            total_records = sum(
                sum(len(term["exams"]) + len(term["zachets"]) + len(term["other"])
                    for term in year["terms"])
                for ed in zachetka["education_details"]
                for year in ed["study_years"]
            )
            logger.info(f"Zachetka synced for tg_id={record.tg_id}: {total_records} records")
    except Exception as _e:
        logger.warning(f"Zachetka fetch failed for tg_id={record.tg_id}: {_e}")

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
        academic_years = specialities[0].get("AcademicYears", [])
        # Определяем текущий год обучения из profile_details (поле Course)
        current_course = None
        if record.profile_details:
            try:
                current_course = int(record.profile_details[0].get("course", 0))
            except (ValueError, TypeError):
                pass
        # Собираем термы с индексом года (0 = первый год, N-1 = последний)
        indexed_terms = []
        for year_idx, ay in enumerate(academic_years):
            for term in ay.get("Terms", []):
                term["_year_name"] = ay.get("Name", "")
                term["_year_idx"] = year_idx
                indexed_terms.append(term)
        # Сортируем: текущий год вперёд, внутри года — по убыванию (последний семестр первый)
        # Если current_course известен — это индекс года (1-based → 0-based = current_course-1)
        current_year_idx = (current_course - 1) if current_course else (len(academic_years) - 1)
        current_year_idx = max(0, min(current_year_idx, len(academic_years) - 1))
        terms = sorted(
            indexed_terms,
            key=lambda t: (
                0 if t["_year_idx"] == current_year_idx else 1,  # текущий год первым
                -t["_year_idx"],                                   # остальные — от новых к старым
            )
        )

    if not student_id:
        logger.warning("student_id not found in viewModel")
        return {"courses": [], "grades": {}, "files": [], "links": []}

    if record.student_id != student_id:
        await record.set({"student_id": student_id})

    total_terms = len(terms)
    done_terms  = 0
    if total_terms > 0:
        await record.set({"sync_total_terms": total_terms, "sync_progress": 5})

    for term in terms:
        term_id = term.get("id") or term.get("Id") or term.get("termId")
        if not term_id:
            done_terms += 1
            continue

        for _attempt in range(3):
            try:
                courses = await client.get_courses(student_id, term_id)
                break
            except httpx.ReadTimeout:
                if _attempt < 2:
                    logger.warning(f"Term {term_id} get_courses ReadTimeout, retry {_attempt+1}/3")
                    await asyncio.sleep(5 * (_attempt + 1))
                else:
                    logger.warning(f"Term {term_id} get_courses ReadTimeout — skipped after 3 attempts")
                    courses = []
            except Exception as e:
                logger.warning(f"Term {term_id} get_courses failed: {e}")
                courses = []
                break
        if not courses and courses == []:
            done_terms += 1
            pct = 5 + int(done_terms / max(total_terms, 1) * 90)
            await record.set({"sync_done_terms": done_terms, "sync_progress": pct,
                               "sync_loaded_term_ids": list(record.sync_loaded_term_ids or []) + [term_id]})
            continue

        for course in courses:
            course["term_id"]   = term_id
            term_name = term.get("_year_name", "") + " " + term.get("Name", term.get("name", ""))
            course["term_name"] = term_name.strip()
            course["lessons"]   = {}

        # Параллельная загрузка занятий для всех курсов семестра
        lesson_tasks = []
        for ci, course in enumerate(courses):
            for lt in course.get("LessonTypes", []):
                lt_id = lt.get("Id")
                if lt_id:
                    lesson_tasks.append((lt_id, lt.get("Name", str(lt_id)), ci))

        if lesson_tasks:
            LESSON_CONCURRENCY = 6
            LESSON_TIMEOUT     = 25
            sem = asyncio.Semaphore(LESSON_CONCURRENCY)

            async def _fetch_one(lt_id, lt_name, ci):
                async with sem:
                    for attempt in range(2):
                        try:
                            lessons = await asyncio.wait_for(
                                client.get_lessons(lt_id, student_id),
                                timeout=LESSON_TIMEOUT,
                            )
                            if lessons:
                                courses[ci]["lessons"][lt_name] = lessons
                                # Собираем файлы из уроков
                                for lesson in lessons:
                                    for f in lesson.get("files", []):
                                        if f.get("url"):
                                            all_files.append({**f, "course_id": str(courses[ci].get("Id", "")), "course_name": courses[ci].get("Name", "")})
                            return
                        except asyncio.TimeoutError:
                            if attempt == 0:
                                logger.warning(f"GetLessons timeout lt_id={lt_id}, retry")
                                await asyncio.sleep(2)
                            else:
                                logger.warning(f"GetLessons timeout lt_id={lt_id} — skipped")
                                return
                        except Exception as e:
                            logger.warning(f"GetLessons failed lt_id={lt_id}: {e.__class__.__name__}: {e}")
                            return

            await asyncio.gather(*[_fetch_one(lt_id, lt_name, ci) for lt_id, lt_name, ci in lesson_tasks])

        all_courses.extend(courses)

        done_terms += 1
        pct = 5 + int(done_terms / max(total_terms, 1) * 90)
        loaded_ids = list(record.sync_loaded_term_ids or []) + [term_id]
        await record.set({
            "sync_done_terms":     done_terms,
            "sync_progress":       pct,
            "sync_courses_found":  len(all_courses),
            "courses":             all_courses,
            "sync_loaded_term_ids": loaded_ids,
        })

    # Дедупликация файлов
    seen, unique_files = set(), []
    for f in all_files:
        if f["url"] not in seen:
            seen.add(f["url"])
            unique_files.append(f)

    return {"courses": all_courses, "grades": all_grades, "files": unique_files, "links": all_links}


async def sync_profiles_due() -> dict:
    """
    Синхронизирует профили пользователей, у которых profile_synced_at
    отсутствует или старше 3 дней. Запускается планировщиком.
    """
    from app.ecampus.queue import get_queue, ECampusTask, Priority

    threshold = datetime.now(timezone.utc) - timedelta(days=3)

    records = await ECampusSyncRecord.find(
        ECampusSyncRecord.enabled == True,  # noqa
        ECampusSyncRecord.sync_status == "ok",
    ).to_list()

    queue = get_queue()
    count = 0
    for record in records:
        synced_at = getattr(record, "profile_synced_at", None)
        if synced_at and synced_at.tzinfo is None:
            synced_at = synced_at.replace(tzinfo=timezone.utc)
        if synced_at is not None and synced_at > threshold:
            continue
        task = ECampusTask(
            task_type="sync_profile",
            tg_id=record.tg_id,
            priority=Priority.LOW,
            payload={},
        )
        await queue.enqueue(task)
        count += 1

    logger.info(f"sync_profiles_due: enqueued {count} profile syncs")
    return {"enqueued": count}

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


# ── Retry упавших синхронизаций ───────────────────────────────────────────────

#: Максимальное число автоматических повторов после ошибки синхронизации.
MAX_SYNC_RETRIES = 3
#: Базовая задержка для экспоненциального backoff (минуты).
RETRY_BACKOFF_BASE_MIN = 15


async def retry_failed_syncs() -> dict:
    """
    Перезапускает синхронизации в статусе 'error' с учётом retry_count и
    времени последней попытки (экспоненциальный backoff).

    Логика:
      - Берём записи с sync_status='error' и retry_count < MAX_SYNC_RETRIES.
      - Проверяем что прошло достаточно времени: delay = RETRY_BACKOFF_BASE_MIN * 2^retry_count.
      - Ставим задачу в очередь (LOW priority) и инкрементируем retry_count.

    Вызывается планировщиком каждые 2 часа.
    """
    from app.ecampus.queue import get_queue, ECampusTask, Priority

    now = datetime.now(timezone.utc)
    records = await ECampusSyncRecord.find(
        ECampusSyncRecord.sync_status == "error",
        ECampusSyncRecord.enabled == True,  # noqa
    ).to_list()

    queue   = get_queue()
    count   = 0
    skipped = 0

    for record in records:
        retry_count = getattr(record, "retry_count", 0) or 0
        if retry_count >= MAX_SYNC_RETRIES:
            skipped += 1
            continue

        # Экспоненциальный backoff: 15м → 30м → 60м
        delay_minutes = RETRY_BACKOFF_BASE_MIN * (2 ** retry_count)
        last_sync = getattr(record, "last_sync", None) or getattr(record, "updated_at", None)

        if last_sync:
            # Если last_sync naive — сделаем aware
            if last_sync.tzinfo is None:
                from datetime import timezone as _tz
                last_sync = last_sync.replace(tzinfo=_tz.utc)
            elapsed_min = (now - last_sync).total_seconds() / 60
            if elapsed_min < delay_minutes:
                skipped += 1
                logger.debug(
                    f"retry_failed_syncs: tg_id={record.tg_id} skipped, "
                    f"only {elapsed_min:.0f}m elapsed (need {delay_minutes}m)"
                )
                continue

        # Инкрементируем счётчик ДО постановки в очередь
        await record.set({"retry_count": retry_count + 1})

        task = ECampusTask(
            task_type="sync_all",
            tg_id=record.tg_id,
            priority=Priority.LOW,
            payload={"is_retry": True, "retry_attempt": retry_count + 1},
        )
        await queue.enqueue(task)
        count += 1
        logger.info(
            f"retry_failed_syncs: enqueued tg_id={record.tg_id} "
            f"attempt={retry_count + 1}/{MAX_SYNC_RETRIES}"
        )

    logger.info(f"retry_failed_syncs: enqueued={count} skipped={skipped}")
    return {"enqueued": count, "skipped": skipped}
