"""
extra_handlers.py — Дополнительные команды бота.

Команды:
  /classmates  — список одногруппников (студентам)
  /teacher     — поиск и профиль преподавателя
  /me          — личный кабинет с кнопками навигации
"""
from __future__ import annotations

import asyncio
from typing import Optional

from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
)
from loguru import logger

from app.core.config import settings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _motor_teachers():
    """Motor-коллекция teachers из ncfu_schedule."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import settings as _s
    return AsyncIOMotorClient(_s.mongo_uri)[_s.mongo_db]["teachers"]


def _motor_lessons():
    """Motor-коллекция lessons из ncfu_schedule."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import settings as _s
    return AsyncIOMotorClient(_s.mongo_uri)[_s.mongo_db]["lessons"]


def _motor_auth_users():
    """Motor-коллекция auth_users из ncfu_auth."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import settings as _s
    return AsyncIOMotorClient(_s.mongo_uri)[_s.auth_mongo_db]["auth_users"]


async def _get_auth_user(tg_id: int) -> dict | None:
    """Возвращает пользователя как dict (motor) или None."""
    try:
        return await _motor_auth_users().find_one({"tg_id": tg_id})
    except Exception as e:
        logger.warning(f"_get_auth_user failed tg_id={tg_id}: {e}")
        return None


def _profile_group(user) -> tuple[Optional[int], Optional[str]]:
    """Извлекает profile_group_id/name из miniapp_settings."""
    s = (user.get("miniapp_settings") or {}) if isinstance(user, dict) else (getattr(user, "miniapp_settings", None) or {})
    return s.get("profile_group_id"), s.get("profile_group_name")


# ══════════════════════════════════════════════════════════════════════════════
# /classmates — список одногруппников
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_classmates(message: Message) -> None:
    """
    Показывает список зарегистрированных студентов в группе пользователя.
    Ищет всех AuthUser у которых profile_group_id совпадает.
    """
    tg_user = message.from_user
    if not tg_user:
        return

    user = await _get_auth_user(tg_user.id)
    if not user:
        await message.answer("👤 Не удалось найти ваш профиль.", parse_mode="HTML")
        return

    group_id, group_name = _profile_group(user)
    if not group_id and not group_name:
        await message.answer(
            "👥 <b>Группа не настроена</b>\n\n"
            "Настройте профиль на сайте, чтобы видеть одногруппников.",
            parse_mode="HTML",
        )
        return

    # Ищем всех с той же группой через motor (AuthUser не имеет индекса по miniapp_settings)
    try:
        col = _motor_auth_users()
        if group_id:
            filter_q = {"miniapp_settings.profile_group_id": group_id}
        else:
            filter_q = {"miniapp_settings.profile_group_name": group_name}

        cursor = col.find(filter_q, {"tg_id": 1, "first_name": 1, "last_name": 1, "username": 1})
        classmates_raw = await cursor.to_list(length=200)
    except Exception as e:
        logger.warning(f"classmates query failed: {e}")
        await message.answer("❌ Ошибка при получении списка одногруппников.", parse_mode="HTML")
        return

    # Убираем самого пользователя, сортируем
    classmates = [c for c in classmates_raw if c.get("tg_id") != tg_user.id]
    classmates.sort(key=lambda c: (c.get("last_name") or "", c.get("first_name") or ""))

    # Убираем самого пользователя из списка, сортируем по имени
    classmates = [c for c in classmates if c.tg_id != tg_user.id]
    classmates.sort(key=lambda c: (c.last_name or "", c.first_name or ""))

    group_label = group_name or f"группа #{group_id}"

    if not classmates:
        await message.answer(
            f"👥 <b>Одногруппники · {group_label}</b>\n\n"
            "Пока никто из вашей группы не зарегистрировался в боте.",
            parse_mode="HTML",
        )
        return

    lines = [f"👥 <b>Одногруппники · {group_label}</b>\n"]
    lines.append(f"<i>Зарегистрировано: {len(classmates)} чел.</i>\n")

    for i, c in enumerate(classmates, 1):
        parts = [p for p in [c.get("last_name"), c.get("first_name")] if p]
        full = " ".join(parts) or c.get("first_name") or f"tg:{c.get('tg_id')}"
        username = f"  @{c['username']}" if c.get("username") else ""
        lines.append(f"{i}. {full}{username}")

    # Telegram ограничивает сообщение 4096 символами
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n<i>…и ещё</i>"

    await message.answer(text, parse_mode="HTML")


# ══════════════════════════════════════════════════════════════════════════════
# /teacher — поиск преподавателя
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_teacher(message: Message) -> None:
    """
    /teacher           — запрос имени (FSM-lite через inline кнопки не нужен)
    /teacher Фамилия   — сразу поиск
    """
    text = message.text or ""
    parts = text.split(maxsplit=1)
    query = parts[1].strip() if len(parts) > 1 else ""

    if not query:
        await message.answer(
            "👤 <b>Поиск преподавателя</b>\n\n"
            "Напишите фамилию (или часть):\n"
            "<code>/teacher Иванов</code>",
            parse_mode="HTML",
        )
        return

    await _do_teacher_search(message, query)


async def _do_teacher_search(message: Message, query: str) -> None:
    """Выполняет поиск и показывает результаты или профиль."""
    try:
        col = _motor_teachers()
        cursor = col.find(
            {"full_name": {"$regex": query, "$options": "i"}},
            {"teacher_id": 1, "full_name": 1, "short_name": 1,
             "subjects": 1, "lesson_types": 1, "group_names": 1,
             "group_ids": 1, "institute_names": 1, "lessons_count": 1,
             "schedule_scraped_at": 1},
        ).limit(8)
        results = await cursor.to_list(length=8)
    except Exception as e:
        logger.warning(f"teacher search failed: {e}")
        await message.answer("❌ Ошибка поиска.", parse_mode="HTML")
        return

    if not results:
        await message.answer(
            f"🔍 По запросу <b>{query}</b> ничего не найдено.\n\n"
            "Попробуйте другую фамилию.",
            parse_mode="HTML",
        )
        return

    if len(results) == 1:
        await _show_teacher_profile(message, results[0])
        return

    # Несколько результатов — показываем список
    buttons = [
        [InlineKeyboardButton(
            text=t.short_name or t.full_name,
            callback_data=f"teacher:{t.teacher_id}",
        )]
        for t in results
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        f"🔍 Найдено преподавателей: <b>{len(results)}</b>\n\nВыберите:",
        parse_mode="HTML",
        reply_markup=kb,
    )


async def _show_teacher_profile(message_or_query, teacher) -> None:
    """Рендерит полный профиль преподавателя с кнопками."""
    from datetime import date

    # teacher — dict (motor) или объект
    def _f(key, default=None):
        return teacher.get(key, default) if isinstance(teacher, dict) else getattr(teacher, key, default)

    full_name   = _f("full_name", "?")
    short_name  = _f("short_name") or full_name
    teacher_id  = _f("teacher_id", 0)
    subjects    = _f("subjects") or []
    lesson_types = _f("lesson_types") or []
    group_names  = _f("group_names") or []
    inst_names   = _f("institute_names") or []
    lessons_cnt  = _f("lessons_count") or 0
    scraped      = _f("schedule_scraped_at")

    lines = [f"👤 <b>{full_name}</b>\n"]

    if inst_names:
        lines.append(f"🏛 {', '.join(inst_names[:2])}")

    if subjects:
        lines.append(f"\n📚 <b>Предметы:</b>")
        for s in subjects[:6]:
            lines.append(f"  • {s}")
        if len(subjects) > 6:
            lines.append(f"  <i>…и ещё {len(subjects)-6}</i>")

    if lesson_types:
        lines.append(f"\n🗂 <b>Типы занятий:</b> {', '.join(lesson_types[:4])}")

    if group_names:
        shown = group_names[:8]
        lines.append(f"\n👥 <b>Группы ({len(group_names)}):</b> {', '.join(shown)}")
        if len(group_names) > 8:
            lines.append(f"  <i>…и ещё {len(group_names)-8}</i>")

    if lessons_cnt:
        lines.append(f"\n📊 Занятий в БД: <b>{lessons_cnt}</b>")

    if scraped:
        lines.append("🕐 Расписание: <b>загружено</b>")

    # Статистика из LessonDoc через motor
    try:
        from collections import Counter
        lcol = _motor_lessons()
        lessons = await lcol.find(
            {"teacher_id": teacher_id},
            {"room_name": 1, "building": 1, "lesson_type": 1},
        ).to_list(length=5000)

        if lessons:
            rooms_c: Counter = Counter()
            bldgs_c: Counter = Counter()
            types_c: Counter = Counter()
            for l in lessons:
                if l.get("room_name"):   rooms_c[l["room_name"]] += 1
                if l.get("building"):    bldgs_c[l["building"]]  += 1
                if l.get("lesson_type"): types_c[l["lesson_type"]] += 1

            total = len(lessons)
            lines.append(f"\n📈 <b>Статистика за всё время:</b>")
            lines.append(f"  Всего пар: <b>{total}</b>")

            if types_c:
                top_types = types_c.most_common(3)
                lines.append(f"  Типы: {', '.join(f'{k} ({v})' for k,v in top_types)}")

            if bldgs_c:
                top_b = bldgs_c.most_common(3)
                lines.append(f"  Корпуса: {', '.join(f'{k} ({v})' for k,v in top_b)}")

            if rooms_c:
                top_r = rooms_c.most_common(3)
                lines.append(f"  Аудитории: {', '.join(f'{k} ({v})' for k,v in top_r)}")
    except Exception as e:
        logger.debug(f"teacher stats query failed: {e}")

    text = "\n".join(lines)

    # Кнопки
    app_base    = settings.webhook_base_url.replace("enexus.", "app.enexus.")
    miniapp_url = settings.webhook_base_url.rstrip("/") + "/miniapp"
    from urllib.parse import quote as _q
    schedule_path = f"/schedule?mode=teacher&id={teacher_id}&name={_q(full_name)}"

    from aiogram.types import WebAppInfo as _WebAppInfo
    buttons = [
        [InlineKeyboardButton(
            text="📅 Расписание",
            web_app=_WebAppInfo(url=f"{miniapp_url}{schedule_path}"),
        )],
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if hasattr(message_or_query, "answer"):
        await message_or_query.answer(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
    else:
        await message_or_query.message.answer(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


async def cb_teacher(callback: CallbackQuery) -> None:
    """Показывает профиль преподавателя по teacher_id из callback."""
    await callback.answer()
    try:
        tid = int((callback.data or "").removeprefix("teacher:"))
    except ValueError:
        return

    try:
        col = _motor_teachers()
        teacher = await col.find_one({"teacher_id": tid})
    except Exception as e:
        logger.warning(f"teacher lookup failed: {e}")
        return

    if not teacher:
        await callback.message.answer("❌ Преподаватель не найден.")
        return

    await _show_teacher_profile(callback, teacher)


# ══════════════════════════════════════════════════════════════════════════════
# /me — личный кабинет
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_me(message: Message) -> None:
    """
    Личный кабинет — показывает профиль пользователя
    и набор кнопок быстрого доступа.
    """
    tg_user = message.from_user
    if not tg_user:
        return

    user = await _get_auth_user(tg_user.id)
    if not user:
        await message.answer("👤 Профиль не найден.", parse_mode="HTML")
        return

    ms   = (user.get("miniapp_settings") or {})
    group_id, group_name = _profile_group(user)
    role = ms.get("profile_role", "")
    is_teacher = role == "teacher"

    # ── Шапка ──────────────────────────────────────────────────────────────
    name_parts = [p for p in [tg_user.first_name, tg_user.last_name] if p]
    full_name  = " ".join(name_parts) or f"tg:{tg_user.id}"
    username   = f"@{tg_user.username}" if tg_user.username else ""

    role_emoji = "🎓" if role == "student" else "👤" if role == "teacher" else "❓"
    role_label = "Студент" if role == "student" else "Преподаватель" if role == "teacher" else "Не настроен"

    profile_str = ""
    if role == "student" and group_name:
        profile_str = f"\n📌 Группа: <b>{group_name}</b>"
    elif role == "teacher":
        t_name = ms.get("profile_teacher_name")
        if t_name:
            profile_str = f"\n📌 Преподаватель: <b>{t_name}</b>"

    # Квота
    quota_str = ""
    try:
        from app.bot.middlewares.anti_flood import get_quota_status
        qs = await get_quota_status(tg_user.id, tg_user.id, "private")
        used, cap = qs["used"], qs["cap"]
        pct = int(used / cap * 100) if cap else 0
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        quota_str = f"\n\n💬 Лимит запросов: <code>{bar}</code> {used}/{cap}"
    except Exception:
        pass

    lines = [
        f"👤 <b>Личный кабинет</b>\n",
        f"{role_emoji} {full_name}",
        username,
        f"<i>{role_label}</i>",
        profile_str,
        quota_str,
    ]
    text = "\n".join(l for l in lines if l)

    # ── Кнопки ─────────────────────────────────────────────────────────────
    miniapp_url = settings.webhook_base_url.rstrip("/") + "/miniapp"
    from urllib.parse import quote as _q

    def _wa(path: str) -> WebAppInfo:
        """WebApp кнопка открывающая miniapp с нужным path."""
        return WebAppInfo(url=f"{miniapp_url}{path}")

    buttons: list[list] = []

    # Расписание
    if role == "student" and group_id:
        path = f"/schedule?mode=group&id={group_id}&name={_q(group_name or '')}"
        buttons.append([InlineKeyboardButton(text="📅 Моё расписание", web_app=_wa(path))])
    elif role == "teacher":
        t_id   = ms.get("profile_teacher_id")
        t_name = ms.get("profile_teacher_name", "")
        if t_id:
            path = f"/schedule?mode=teacher&id={t_id}&name={_q(t_name)}"
            buttons.append([InlineKeyboardButton(text="📅 Моё расписание", web_app=_wa(path))])

    # Mini App главная
    buttons.append([InlineKeyboardButton(
        text="📱 Расписание (приложение)",
        web_app=WebAppInfo(url=miniapp_url),
    )])

    # Предметы / занятия
    if role == "student":
        buttons.append([
            InlineKeyboardButton(text="📚 Предметы", web_app=_wa("/ecampus")),
            InlineKeyboardButton(text="📊 Статистика", callback_data="me:stats"),
        ])
        if group_name:
            buttons.append([InlineKeyboardButton(text="👥 Одногруппники", callback_data="me:classmates")])
    elif role == "teacher":
        buttons.append([InlineKeyboardButton(text="📈 Мои занятия", web_app=_wa("/teacher"))])

    # Профиль и карта
    buttons.append([
        InlineKeyboardButton(text="⚙️ Профиль", web_app=_wa("/profile")),
        InlineKeyboardButton(text="🗺 Карта",    web_app=_wa("/map")),
    ])
    buttons.append([
        InlineKeyboardButton(text="💬 Лимит запросов", callback_data="me:limit"),
        InlineKeyboardButton(text="❓ Помощь",          callback_data="me:help"),
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


async def cb_me(callback: CallbackQuery) -> None:
    """Обработчик кнопок личного кабинета."""
    await callback.answer()
    action = (callback.data or "").removeprefix("me:")
    tg_user = callback.from_user
    if not tg_user:
        return

    if action == "stats":
        from app.bot.handlers.grades import cmd_stats, _get_ecampus_record, _build_stats_keyboard
        rec = await _get_ecampus_record(tg_user.id)
        if not rec or not rec.get("courses"):
            await callback.message.answer("📭 Нет данных eCampus.", parse_mode="HTML")
            return
        kb = _build_stats_keyboard(rec["courses"])
        await callback.message.answer(
            "📊 <b>Статистика успеваемости</b>\n\nВыберите период:",
            parse_mode="HTML",
            reply_markup=kb,
        )

    elif action == "classmates":
        from aiogram.types import Message as _Msg
        await cmd_classmates(callback.message)

    elif action == "limit":
        try:
            from app.bot.handlers.commands import cmd_limit
            await cmd_limit(callback.message)
        except Exception as e:
            logger.warning(f"cb_me limit failed: {e}")

    elif action == "help":
        await callback.message.answer(
            "📖 <b>Быстрая справка</b>\n\n"
            "/me       — этот экран\n"
            "/grades   — оценки из eCampus\n"
            "/stats    — статистика (с выбором семестра)\n"
            "/subjects — список предметов\n"
            "/teacher  — поиск преподавателя\n"
            "/classmates — одногруппники\n"
            "/limit    — лимит запросов\n"
            "/miniapp  — открыть приложение\n"
            "/help     — полная справка",
            parse_mode="HTML",
        )
