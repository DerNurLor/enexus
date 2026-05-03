"""
grades.py — Команды для работы с оценками из eCampus.

Команды:
  /grades              — все оценки текущего семестра (таблица)
  /grades <семестр>    — оценки конкретного семестра (1–8)
  /stats               — статистика: ср. рейтинг, экзамены, зачёты, фото-chart
  /subjects            — список предметов с типами занятий и рейтингом

Доступ к данным: напрямую через motor → коллекция ecampus_sync (ncfu_schedule DB).
ECampusSyncRecord НЕ импортируется через beanie (другой сервис), используем
raw motor-запрос.
"""
from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any, Optional

from aiogram.types import Message, BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from app.core.config import settings

# ── Маппинг типов занятий (совпадает с web/app/ecampus/page.tsx) ──────────────
LESSON_TYPE_NAMES: dict[int, str] = {
    1: "Лекция",       2: "Семинар",     3: "Практика",
    4: "Экзамен",      5: "Зачёт",       6: "Курсовая",
    8: "Лаб.",         12: "Контрольная", 14: "Практ.пр.",
    23: "Сам.работа",  55: "Диф.зачёт",  57: "Предд.пр.",
}
EXAM_TYPES   = {4}
CREDIT_TYPES = {5, 55}

# ── Маппинг семестров → «N курс, M семестр» ──────────────────────────────────
TERM_MAP: dict[int, tuple[int, int]] = {
    248155: (1, 1), 248156: (1, 2),
    248157: (2, 1), 248158: (2, 2),
    248159: (3, 1), 248160: (3, 2),
    248161: (4, 1), 248162: (4, 2),
}

GRADE_EMOJI: dict[str, str] = {
    "отлично":              "🟢",
    "хорошо":               "🔵",
    "удовлетворительно":    "🟡",
    "неудовлетворительно":  "🔴",
    "зачтено":              "✅",
    "не зачтено":           "❌",
}

# ── Стиль графиков ────────────────────────────────────────────────────────────

_STYLE: dict = {
    "font.family":    "DejaVu Sans",
    "font.size":      11,
    "axes.facecolor": "#1e1e2e",
    "figure.facecolor":"#12121f",
    "text.color":     "#cdd6f4",
    "axes.labelcolor":"#cdd6f4",
    "xtick.color":    "#a6adc8",
    "ytick.color":    "#a6adc8",
    "axes.edgecolor": "#313244",
    "grid.color":     "#313244",
    "axes.grid":      True,
    "grid.alpha":     0.4,
    "axes.spines.top":   False,
    "axes.spines.right": False,
}

_GRADE_COLORS: dict[str, str] = {
    "отлично":            "#a6e3a1",
    "хорошо":             "#89b4fa",
    "удовлетворительно":  "#f9e2af",
    "неудовлетворительно":"#f38ba8",
    "зачтено":            "#94e2d5",
    "не зачтено":         "#f38ba8",
}

_GRADE_ORDER = [
    "отлично", "хорошо", "удовлетворительно",
    "неудовлетворительно", "зачтено", "не зачтено",
]


def _fig_to_buf(fig) -> bytes:
    """Рендерит matplotlib Figure в PNG bytes и закрывает figure."""
    import io
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=140)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _build_stats_chart(
    grade_counts: dict[str, int],
    zachetka_counts: dict[str, int] | None,
    by_term: dict[int, list[dict]],
    all_grades: list[dict],
    title_suffix: str = "",
):
    """
    Одно изображение 2×2 (или 1×2 если мало данных):
      [A] Круговая: оценки из занятий  |  [B] Круговая: зачётная книжка
      [C] Рейтинг по семестрам (бар)   |  [D] Таймлайн оценок
    Если нет зачётки — A занимает всю первую строку.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    import numpy as np
    from datetime import datetime as _dt

    HAS_ZACHETKA = bool(zachetka_counts and sum(zachetka_counts.values()) > 0)
    HAS_TIMELINE = len(all_grades) >= 3
    HAS_RATING   = any((c.get("MaxRating") or 0) > 0 for cs in by_term.values() for c in cs)

    STYLE = {
        "font.family":    "DejaVu Sans",
        "font.size":      10,
        "axes.facecolor": "#1e1e2e",
        "figure.facecolor":"#12121f",
        "text.color":     "#cdd6f4",
        "axes.labelcolor":"#cdd6f4",
        "xtick.color":    "#a6adc8",
        "ytick.color":    "#a6adc8",
        "axes.edgecolor": "#313244",
        "grid.color":     "#313244",
        "axes.grid":      True,
        "grid.alpha":     0.3,
        "axes.spines.top":   False,
        "axes.spines.right": False,
    }
    COLORS = {
        "отлично":            "#a6e3a1",
        "хорошо":             "#89b4fa",
        "удовлетворительно":  "#f9e2af",
        "неудовлетворительно":"#f38ba8",
        "зачтено":            "#94e2d5",
        "не зачтено":         "#f38ba8",
    }
    ORDER = ["отлично","хорошо","удовлетворительно","неудовлетворительно","зачтено","не зачтено"]

    def _pie_data(counts):
        labels, sizes, colors = [], [], []
        for g in ORDER:
            if counts.get(g, 0): labels.append(g.capitalize()); sizes.append(counts[g]); colors.append(COLORS[g])
        for g, v in counts.items():
            if g not in COLORS and v: labels.append(g.capitalize()); sizes.append(v); colors.append("#b4befe")
        return labels, sizes, colors

    def _draw_donut(ax, counts, title, main=True):
        labels, sizes, colors = _pie_data(counts)
        if not sizes:
            ax.axis("off"); ax.set_title(title, fontsize=11 if main else 9, fontweight="bold", color="#cdd6f4", pad=8); return
        width = 0.55 if main else 0.48
        wedges, _, autotexts = ax.pie(
            sizes, labels=None, colors=colors,
            autopct=lambda p: f"{p:.0f}%" if p > 7 else "",
            pctdistance=0.76,
            wedgeprops={"width": width, "edgecolor": "#12121f", "linewidth": 1.5},
            startangle=90,
        )
        for at in autotexts:
            at.set_color("#12121f"); at.set_fontsize(8 if main else 7); at.set_fontweight("bold")
        total = sum(sizes)
        fs = 13 if main else 10
        ax.text(0, 0, f"{total}\nзап.", ha="center", va="center",
                fontsize=fs, fontweight="bold", color="#cdd6f4", linespacing=1.3)
        ax.legend(wedges, [f"{l} {s}" for l,s in zip(labels,sizes)],
                  loc="lower center", bbox_to_anchor=(0.5, -0.15 if main else -0.12),
                  frameon=False, fontsize=7 if main else 6, ncol=2, labelcolor="#a6adc8")
        ax.set_title(title, fontsize=11 if main else 9, fontweight="bold", color="#cdd6f4", pad=8)

    with plt.rc_context(STYLE):
        # Layout: 2 строки × 2 столбца
        # Строка 1: donut(s); Строка 2: бар рейтинга + таймлайн
        n_bottom = sum([HAS_RATING, HAS_TIMELINE])
        if n_bottom == 0:
            fig, axes_top = plt.subplots(1, 2 if HAS_ZACHETKA else 1, figsize=(9, 4.5))
            axes_top = [axes_top] if not hasattr(axes_top, "__len__") else list(axes_top)
            axes_bot = []
        else:
            fig = plt.figure(figsize=(10, 8.5))
            gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35,
                                   height_ratios=[1.1, 1])
            if HAS_ZACHETKA:
                axes_top = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
            else:
                ax_top_merged = fig.add_subplot(gs[0, :])
                axes_top = [ax_top_merged]
            axes_bot = []
            if HAS_RATING and HAS_TIMELINE:
                axes_bot = [fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]
            elif HAS_RATING:
                axes_bot = [fig.add_subplot(gs[1, :])]
            elif HAS_TIMELINE:
                axes_bot = [fig.add_subplot(gs[1, :])]

        ttl = f"Статистика успеваемости{title_suffix}"
        fig.suptitle(ttl, fontsize=13, fontweight="bold", color="#cdd6f4", y=0.98)

        # Топ donuts
        if HAS_ZACHETKA and len(axes_top) >= 2:
            _draw_donut(axes_top[0], grade_counts, "Текущие оценки", main=True)
            _draw_donut(axes_top[1], zachetka_counts, "Зачётная книжка", main=False)
        else:
            _draw_donut(axes_top[0], grade_counts, "Распределение оценок", main=True)

        bot_idx = 0

        # Бар рейтинга по семестрам
        if HAS_RATING and axes_bot:
            ax = axes_bot[bot_idx]; bot_idx += 1
            tids = sorted(by_term.keys())
            labels, avgs, maxs = [], [], []
            for tid in tids:
                cs = [c for c in by_term[tid] if (c.get("MaxRating") or 0) > 0]
                if not cs: continue
                avg = sum(c.get("CurrentRating") or 0 for c in cs) / len(cs)
                mx  = sum(c.get("MaxRating") or 0 for c in cs) / len(cs)
                info = TERM_MAP.get(tid)
                labels.append(f"{info[0]}к{info[1]}с" if info else str(tid))
                avgs.append(avg); maxs.append(mx)
            if labels:
                x = np.arange(len(labels))
                ax.bar(x, maxs, 0.55, color="#313244", zorder=2, label="Макс.")
                bar_colors = ["#a6e3a1" if a/m>=0.7 else "#f9e2af" if a/m>=0.5 else "#f38ba8"
                              for a,m in zip(avgs,maxs)]
                bars = ax.bar(x, avgs, 0.55, color=bar_colors, zorder=3, label="Факт.")
                for bar, val, mx in zip(bars, avgs, maxs):
                    pct = val/mx*100 if mx else 0
                    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                            f"{pct:.0f}%", ha="center", va="bottom", fontsize=7.5, color="#cdd6f4")
                ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
                ax.set_ylabel("Рейтинг", fontsize=8)
                ax.set_ylim(0, max(maxs)*1.18 if maxs else 100)
                ax.legend(frameon=False, fontsize=7, labelcolor="#a6adc8", loc="upper left")
                ax.set_title("Рейтинг по семестрам", fontsize=9, fontweight="bold", color="#cdd6f4", pad=6)

        # Таймлайн
        if HAS_TIMELINE and axes_bot and bot_idx < len(axes_bot):
            ax = axes_bot[bot_idx]
            SCORE = {"отлично":4,"хорошо":3,"удовлетворительно":2,"неудовлетворительно":1,"зачтено":4,"не зачтено":1}
            pts = []
            for r in all_grades:
                if not r.get("date"): continue
                try:
                    d = _dt.fromisoformat(r["date"][:10])
                    y = SCORE.get(r["grade"].lower(), 2.5)
                    c = COLORS.get(r["grade"].lower(), "#b4befe")
                    pts.append((d, y, c))
                except Exception: pass
            if len(pts) >= 3:
                pts.sort(key=lambda x: x[0])
                dates = [p[0] for p in pts]; ys = [p[1] for p in pts]; clrs = [p[2] for p in pts]
                ys_arr = np.array(ys, dtype=float)
                w = min(7, len(ys_arr))
                ma = np.convolve(ys_arr, np.ones(w)/w, mode="valid")
                import matplotlib.dates as mdates
                ax.scatter(dates, ys, c=clrs, s=40, zorder=5, edgecolors="#12121f", linewidths=0.7, alpha=0.9)
                ax.plot(dates[w-1:], ma, color="#cba6f7", linewidth=1.8, zorder=4, alpha=0.85, label=f"Тренд")
                ax.set_yticks([1,2,3,4])
                ax.set_yticklabels(["Неудовл.","Удовл.","Хорошо","Отл."], fontsize=7.5)
                ax.set_ylim(0.5, 4.5)
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3,maxticks=6))
                fig.autofmt_xdate(rotation=25, ha="right")
                ax.legend(frameon=False, fontsize=7, labelcolor="#cba6f7", loc="upper left")
                ax.set_title("Динамика успеваемости", fontsize=9, fontweight="bold", color="#cdd6f4", pad=6)

        fig.tight_layout(rect=[0, 0, 1, 0.97])
    return fig


def _build_charts(
    grade_counts: dict[str, int],
    by_term: dict[int, list[dict]],
    all_grades: list[dict],
    zachetka_counts: dict[str, int] | None = None,
    title_suffix: str = "",
) -> list:
    """Строит один большой chart, возвращает список из одной figure."""
    try:
        fig = _build_stats_chart(grade_counts, zachetka_counts, by_term, all_grades, title_suffix)
        return [fig]
    except Exception as exc:
        logger.warning(f"_build_stats_chart failed: {exc}")
        return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _motor_col():
    """Возвращает motor-коллекцию ecampus_sync из ncfu_schedule DB."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(settings.mongo_uri)
    return client[settings.mongo_db]["ecampus_sync"]


async def _get_ecampus_record(tg_id: int) -> Optional[dict]:
    """Загружает ECampusSyncRecord для пользователя. None если не подключён."""
    col = _motor_col()
    return await col.find_one({"tg_id": tg_id})


def _term_label(term_id: int) -> str:
    info = TERM_MAP.get(term_id)
    if info:
        return f"{info[0]} курс, {info[1]} сем."
    return f"Сем.{term_id}"


def _collect_grades(courses: list[dict]) -> list[dict]:
    """
    Из списка курсов собирает все оценки в плоский список:
      {course_name, term_id, lesson_type_name, date, grade, score, room}
    """
    rows: list[dict] = []
    for c in courses:
        cname = c.get("Name") or c.get("name") or "?"
        term_id = c.get("term_id") or 0
        lessons_by_type: dict[str, list] = c.get("lessons") or {}
        for _lt_name, lessons in lessons_by_type.items():
            if not isinstance(lessons, list):
                continue
            for l in lessons:
                grade = (l.get("GradeText") or "").strip()
                if not grade:
                    continue
                rows.append({
                    "course":    cname,
                    "term_id":   term_id,
                    "lt_name":   _lt_name,
                    "date":      l.get("Date") or "",
                    "grade":     grade,
                    "score":     l.get("GainedScore") or 0,
                    "room":      l.get("Room") or "",
                })
    rows.sort(key=lambda x: x["date"])
    return rows


def _format_grade_line(row: dict) -> str:
    emoji = GRADE_EMOJI.get(row["grade"].lower(), "⚪")
    course_short = row["course"][:35] + "…" if len(row["course"]) > 36 else row["course"]
    score_str = f"  <i>+{row['score']:.1f}</i>" if row["score"] else ""
    date_str = ""
    if row["date"]:
        try:
            d = datetime.fromisoformat(row["date"])
            date_str = f"  <code>{d.strftime('%d.%m')}</code>"
        except Exception:
            pass
    return f"{emoji} <b>{course_short}</b> — {row['grade']}{score_str}{date_str}"


def _collect_grades_zachetka(zachetka: dict) -> list[dict]:
    """
    Из зачётной книжки собирает плоский список всех итоговых записей.
    Возвращает: [{year, term, discipline, mark, date, type}]
    """
    rows: list[dict] = []
    for ed in (zachetka.get("education_details") or []):
        for year in (ed.get("study_years") or []):
            for term in (year.get("terms") or []):
                for cat in ["exams", "zachets", "other"]:
                    for item in (term.get(cat) or []):
                        mark = (item.get("mark") or "").strip()
                        if not mark:
                            continue
                        rows.append({
                            "discipline": (item.get("discipline") or "").strip(),
                            "mark":       mark,
                            "date":       (item.get("date") or "")[:10],
                            "type":       (item.get("type") or "").strip(),
                            "year":       year.get("name", ""),
                            "term":       term.get("name", ""),
                        })
    rows.sort(key=lambda x: x["date"])
    return rows


def _current_term_id(courses: list[dict]) -> Optional[int]:
    """Возвращает наибольший term_id (текущий семестр)."""
    ids = [c.get("term_id") for c in courses if c.get("term_id")]
    return max(ids) if ids else None


def _parse_sem_arg(text: str) -> Optional[int]:
    """Из '/grades 3' извлекает 3, иначе None."""
    m = re.search(r'\b([1-8])\b', text)
    return int(m.group(1)) if m else None


def _find_term_by_sem(sem: int) -> list[int]:
    """Возвращает term_id-ы, соответствующие семестру 1–8."""
    result = []
    for tid, (course, s) in TERM_MAP.items():
        if (course - 1) * 2 + s == sem:
            result.append(tid)
    return result


# ── /grades ───────────────────────────────────────────────────────────────────

async def cmd_grades(message: Message) -> None:
    """Показывает оценки: текущий семестр или семестр по номеру."""
    tg_user = message.from_user
    if not tg_user:
        return

    text = message.text or ""
    sem_arg = _parse_sem_arg(text.split(maxsplit=1)[1]) if len(text.split()) > 1 else None

    rec = await _get_ecampus_record(tg_user.id)
    if not rec:
        await message.answer(
            "📚 <b>eCampus не подключён</b>\n\n"
            "Подключите аккаунт eCampus в разделе <b>Профиль → eCampus</b> на сайте "
            "или в мини-приложении.",
            parse_mode="HTML",
        )
        return

    if rec.get("sync_status") == "running":
        await message.answer(
            "⏳ Синхронизация с eCampus ещё идёт — данные обновляются.\n"
            "Попробуйте через минуту.",
            parse_mode="HTML",
        )
        return

    courses: list[dict] = rec.get("courses") or []
    if not courses:
        await message.answer(
            "📭 Данные eCampus пока пусты.\n"
            "Нажмите «Обновить» в мини-приложении или подождите автосинхронизации.",
            parse_mode="HTML",
        )
        return

    # Фильтрация по семестру
    if sem_arg is not None:
        target_terms = _find_term_by_sem(sem_arg)
        filtered_courses = [c for c in courses if c.get("term_id") in target_terms]
        sem_label = f"Семестр {sem_arg}"
    else:
        cur_term = _current_term_id(courses)
        filtered_courses = [c for c in courses if c.get("term_id") == cur_term]
        sem_label = _term_label(cur_term) if cur_term else "Текущий семестр"

    grades = _collect_grades(filtered_courses)

    if not grades:
        await message.answer(
            f"📭 <b>Оценок нет</b> ({sem_label})\n\n"
            "Оценки появятся после того, как преподаватель их выставит.",
            parse_mode="HTML",
        )
        return

    # Группируем по предмету
    by_course: dict[str, list[dict]] = {}
    for row in grades:
        by_course.setdefault(row["course"], []).append(row)

    lines = [f"📊 <b>Оценки · {sem_label}</b>\n"]
    for cname, rows in by_course.items():
        short = cname[:40] + "…" if len(cname) > 41 else cname
        lines.append(f"\n<b>{short}</b>")
        for row in rows:
            emoji = GRADE_EMOJI.get(row["grade"].lower(), "⚪")
            score_str = f" <i>+{row['score']:.1f}</i>" if row["score"] else ""
            date_str = ""
            if row["date"]:
                try:
                    d = datetime.fromisoformat(row["date"])
                    date_str = f" <code>{d.strftime('%d.%m')}</code>"
                except Exception:
                    pass
            lines.append(f"  {emoji} {row['lt_name']}: <b>{row['grade']}</b>{score_str}{date_str}")

    total_graded = len(grades)
    lines.append(f"\n<i>Всего оценок: {total_graded}</i>")

    # Разбиваем на чанки ≤4096 символов
    msg = "\n".join(lines)
    if len(msg) <= 4096:
        await message.answer(msg, parse_mode="HTML")
    else:
        chunk, chunks = [], []
        cur_len = 0
        for line in lines:
            if cur_len + len(line) + 1 > 4000:
                chunks.append("\n".join(chunk))
                chunk, cur_len = [], 0
            chunk.append(line)
            cur_len += len(line) + 1
        if chunk:
            chunks.append("\n".join(chunk))
        for i, ch in enumerate(chunks):
            await message.answer(ch + (f"\n\n<i>({i+1}/{len(chunks)})</i>" if len(chunks) > 1 else ""),
                                 parse_mode="HTML")


# ── /stats ────────────────────────────────────────────────────────────────────

async def _render_stats(
    message_or_query,
    tg_id: int,
    term_filter: str = "all",  # "all" | "current" | "248155" (конкретный term_id)
) -> None:
    """Общая функция рендеринга статистики для /stats и callback."""
    rec = await _get_ecampus_record(tg_id)
    if not rec:
        text = "📚 <b>eCampus не подключён</b>\n\nПодключите аккаунт в разделе Профиль на сайте."
        if hasattr(message_or_query, "answer"):
            await message_or_query.answer(text, parse_mode="HTML")
        else:
            await message_or_query.message.answer(text, parse_mode="HTML")
        return

    all_courses: list[dict] = rec.get("courses") or []
    if not all_courses:
        text = "📭 Нет данных eCampus. Обновите синхронизацию."
        if hasattr(message_or_query, "answer"):
            await message_or_query.answer(text, parse_mode="HTML")
        else:
            await message_or_query.message.answer(text, parse_mode="HTML")
        return

    # ── Фильтрация по семестру ─────────────────────────────────────────────
    title_suffix = ""
    if term_filter == "all":
        courses = all_courses
        title_suffix = " · Всё время"
    elif term_filter == "current":
        cur = _current_term_id(all_courses)
        courses = [c for c in all_courses if c.get("term_id") == cur]
        if cur:
            # Берём реальное название из данных
            sample = next((c for c in all_courses if c.get("term_id") == cur), None)
            raw = (sample.get("term_name") or "").strip() if sample else ""
            if raw:
                title_suffix = f" · {raw}"
            else:
                info = TERM_MAP.get(cur)
                title_suffix = f" · {info[0]}к {info[1]}с" if info else f" · сем.{cur}"
    else:
        # конкретный term_id
        try:
            tid = int(term_filter)
            courses = [c for c in all_courses if c.get("term_id") == tid]
            sample = next((c for c in courses), None)
            raw = (sample.get("term_name") or "").strip() if sample else ""
            if raw:
                title_suffix = f" · {raw}"
            else:
                info = TERM_MAP.get(tid)
                title_suffix = f" · {info[0]}к {info[1]}с" if info else f" · сем.{tid}"
        except ValueError:
            courses = all_courses

    if not courses:
        text = "📭 Нет данных за этот семестр."
        if hasattr(message_or_query, "answer"):
            await message_or_query.answer(text, parse_mode="HTML")
        elif hasattr(message_or_query, "message"):
            await message_or_query.message.answer(text, parse_mode="HTML")
        return

    all_grades   = _collect_grades(courses)
    total_grades = len(all_grades)
    grade_counts: dict[str, int] = {}
    for row in all_grades:
        grade_counts[row["grade"].lower()] = grade_counts.get(row["grade"].lower(), 0) + 1

    with_rating  = [c for c in courses if (c.get("MaxRating") or 0) > 0]
    avg_rating   = sum(c.get("CurrentRating") or 0 for c in with_rating) / len(with_rating) if with_rating else 0
    max_possible = sum(c.get("MaxRating") or 0 for c in with_rating) / len(with_rating) if with_rating else 0
    rating_pct   = avg_rating / max_possible * 100 if max_possible else 0

    by_term: dict[int, list[dict]] = {}
    for c in courses:
        by_term.setdefault(c.get("term_id") or 0, []).append(c)

    exams_total   = sum(1 for c in courses if any(lt.get("LessonType") in EXAM_TYPES for lt in (c.get("LessonTypes") or [])))
    credits_total = sum(1 for c in courses
        if any(lt.get("LessonType") in CREDIT_TYPES for lt in (c.get("LessonTypes") or []))
        and not any(lt.get("LessonType") in EXAM_TYPES for lt in (c.get("LessonTypes") or [])))

    rating_icon = "🟢" if rating_pct >= 70 else ("🟡" if rating_pct >= 50 else "🔴")
    lines = [
        f"📊 <b>Статистика успеваемости{title_suffix}</b>\n",
        f"📚 Предметов:   <b>{len(courses)}</b>",
        f"✏️  Оценок:      <b>{total_grades}</b>",
        f"🎓 Экзаменов:  <b>{exams_total}</b>",
        f"📝 Зачётов:    <b>{credits_total}</b>",
    ]
    if avg_rating > 0:
        lines.append(f"⭐ Рейтинг:    {rating_icon} <b>{avg_rating:.1f}</b> / {max_possible:.1f} ({rating_pct:.0f}%)")

    last_sync = rec.get("last_sync")
    if last_sync:
        try:
            dt = datetime.fromisoformat(str(last_sync))
            lines.append(f"\n<i>Обновлено: {dt.strftime('%d.%m.%Y %H:%M')}</i>")
        except Exception:
            pass

    zachetka = rec.get("zachetka") or {}
    zachetka_rows = _collect_grades_zachetka(zachetka)
    zachetka_counts: dict[str, int] = {}
    for row in zachetka_rows:
        zachetka_counts[row["mark"].lower()] = zachetka_counts.get(row["mark"].lower(), 0) + 1

    charts = _build_charts(grade_counts, by_term, all_grades,
                           zachetka_counts if zachetka_counts else None,
                           title_suffix=title_suffix)
    figs = [f for f in charts if f is not None]
    text = "\n".join(lines)

    # Определяем куда отправлять
    is_callback = isinstance(message_or_query, CallbackQuery)
    send_target = message_or_query.message if is_callback else message_or_query

    if not figs:
        await send_target.answer(text, parse_mode="HTML")
        return

    from aiogram.types import InputMediaPhoto
    buf = _fig_to_buf(figs[0])
    if is_callback:
        await send_target.answer_photo(
            BufferedInputFile(buf, filename="stats.png"),
            caption=text,
            parse_mode="HTML",
        )
    else:
        await send_target.answer_photo(
            BufferedInputFile(buf, filename="stats.png"),
            caption=text,
            parse_mode="HTML",
        )


def _build_stats_keyboard(courses: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора семестра для /stats."""
    by_term: dict[int, str] = {}   # tid → реальное название из term_name
    for c in courses:
        tid = c.get("term_id") or 0
        if not tid:
            continue
        if tid not in by_term:
            # Берём term_name из курса ("3 курс 5 семестр") или fallback из TERM_MAP
            raw = (c.get("term_name") or "").strip()
            if raw:
                by_term[tid] = raw
            else:
                info = TERM_MAP.get(tid)
                by_term[tid] = f"{info[0]}к {info[1]}с" if info else f"Сем.{tid}"

    buttons = []
    cur = _current_term_id(courses)
    row = []
    for tid in sorted(by_term.keys(), reverse=True):
        label = by_term[tid]
        if tid == cur:
            label = f"▶ {label}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"stats:{tid}"))
        if len(row) == 2:          # по 2 в ряд — названия длиннее, иначе не влезают
            buttons.append(row); row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="📊 За всё время", callback_data="stats:all")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def cmd_stats(message: Message) -> None:
    """Статистика успеваемости — показывает выбор семестра, затем рендерит."""
    tg_user = message.from_user
    if not tg_user:
        return

    rec = await _get_ecampus_record(tg_user.id)
    if not rec:
        await message.answer(
            "📚 <b>eCampus не подключён</b>\n\nПодключите аккаунт в разделе Профиль на сайте.",
            parse_mode="HTML",
        )
        return

    courses: list[dict] = rec.get("courses") or []
    if not courses:
        await message.answer("📭 Нет данных eCampus. Обновите синхронизацию.", parse_mode="HTML")
        return

    kb = _build_stats_keyboard(courses)
    await message.answer(
        "📊 <b>Статистика успеваемости</b>\n\n"
        "Выберите период:",
        parse_mode="HTML",
        reply_markup=kb,
    )


async def cb_stats(callback: CallbackQuery) -> None:
    """Обработчик выбора семестра для /stats."""
    await callback.answer()
    if not callback.from_user:
        return
    term_filter = (callback.data or "").removeprefix("stats:")
    await _render_stats(callback, callback.from_user.id, term_filter)
# ── /subjects ─────────────────────────────────────────────────────────────────

async def cmd_subjects(message: Message) -> None:
    """Список предметов текущего семестра с типами занятий и рейтингом."""
    tg_user = message.from_user
    if not tg_user:
        return

    text = message.text or ""
    sem_arg = _parse_sem_arg(text.split(maxsplit=1)[1]) if len(text.split()) > 1 else None

    rec = await _get_ecampus_record(tg_user.id)
    if not rec:
        await message.answer(
            "📚 <b>eCampus не подключён</b>\n\n"
            "Подключите аккаунт в разделе Профиль на сайте.",
            parse_mode="HTML",
        )
        return

    courses: list[dict] = rec.get("courses") or []
    if not courses:
        await message.answer("📭 Нет данных. Обновите синхронизацию.", parse_mode="HTML")
        return

    if sem_arg is not None:
        target_terms = _find_term_by_sem(sem_arg)
        filtered = [c for c in courses if c.get("term_id") in target_terms]
        sem_label = f"Семестр {sem_arg}"
    else:
        cur_term = _current_term_id(courses)
        filtered = [c for c in courses if c.get("term_id") == cur_term]
        sem_label = _term_label(cur_term) if cur_term else "Текущий семестр"

    if not filtered:
        await message.answer(f"📭 Предметы не найдены ({sem_label}).", parse_mode="HTML")
        return

    # Сортируем: сначала с рейтингом (по убыванию)
    filtered.sort(key=lambda c: -(c.get("CurrentRating") or 0))

    lines = [f"📚 <b>Предметы · {sem_label}</b>  ({len(filtered)} шт.)\n"]

    for c in filtered:
        cname = c.get("Name") or c.get("name") or "?"
        short = cname[:45] + "…" if len(cname) > 46 else cname

        # Типы занятий
        lt_list: list[str] = []
        has_exam   = False
        has_credit = False
        for lt in (c.get("LessonTypes") or []):
            lt_id = lt.get("LessonType")
            lt_list.append(LESSON_TYPE_NAMES.get(lt_id, lt.get("Name") or "?"))
            if lt_id in EXAM_TYPES:
                has_exam = True
            if lt_id in CREDIT_TYPES:
                has_credit = True

        type_str = ", ".join(lt_list[:4]) if lt_list else "нет данных"

        # Рейтинг
        cur_r = c.get("CurrentRating") or 0
        max_r = c.get("MaxRating") or 0
        if max_r > 0:
            pct = cur_r / max_r
            r_icon = "🟢" if pct >= 0.7 else ("🟡" if pct >= 0.5 else "🔴")
            rating_str = f"\n    {r_icon} Рейтинг: <b>{cur_r:.1f}</b>/{max_r}"
        else:
            rating_str = ""

        # Итоговый контроль
        control = ""
        if has_exam:
            control = " 🎓<i>Экзамен</i>"
        elif has_credit:
            control = " 📝<i>Зачёт</i>"

        lines.append(f"• <b>{short}</b>{control}")
        lines.append(f"  <i>{type_str}</i>{rating_str}")

    msg = "\n".join(lines)
    if len(msg) <= 4096:
        await message.answer(msg, parse_mode="HTML")
    else:
        # Разбиваем на чанки
        chunks, chunk, cur_len = [], [], 0
        for line in lines:
            if cur_len + len(line) + 1 > 4000:
                chunks.append("\n".join(chunk))
                chunk, cur_len = [], 0
            chunk.append(line)
            cur_len += len(line) + 1
        if chunk:
            chunks.append("\n".join(chunk))
        for i, ch in enumerate(chunks):
            suffix = f"\n\n<i>({i+1}/{len(chunks)})</i>" if len(chunks) > 1 else ""
            await message.answer(ch + suffix, parse_mode="HTML")


# ── /ecampus ──────────────────────────────────────────────────────────────────

async def cmd_ecampus(message: Message) -> None:
    """Общий статус подключения и сводка по данным eCampus."""
    tg_user = message.from_user
    if not tg_user:
        return

    rec = await _get_ecampus_record(tg_user.id)
    if not rec:
        await message.answer(
            "📚 <b>eCampus СКФУ</b>\n\n"
            "Аккаунт <b>не подключён</b>.\n\n"
            "Подключите его в разделе <b>Профиль → eCampus</b> на сайте "
            "или в мини-приложении — и получите:\n"
            "  • Список предметов и оценок\n"
            "  • Статистику успеваемости\n"
            "  • Рейтинги по каждому курсу\n\n"
            "Команды (после подключения):\n"
            "  /grades   — мои оценки\n"
            "  /stats    — статистика успеваемости\n"
            "  /subjects — список предметов",
            parse_mode="HTML",
        )
        return

    courses: list[dict] = rec.get("courses") or []
    sync_status = rec.get("sync_status") or "unknown"
    last_sync   = rec.get("last_sync")

    status_map = {
        "ok":      "✅ Синхронизировано",
        "running": "⏳ Синхронизация...",
        "error":   "❌ Ошибка синхронизации",
        "pending": "🕐 Ожидание синхронизации",
    }
    status_str = status_map.get(sync_status, f"❓ {sync_status}")

    all_grades = _collect_grades(courses)
    cur_term   = _current_term_id(courses)
    cur_courses = [c for c in courses if c.get("term_id") == cur_term]

    lines = [
        "📚 <b>eCampus СКФУ</b>\n",
        f"🔗 Статус: {status_str}",
        f"📦 Предметов: <b>{len(courses)}</b>",
        f"✏️  Оценок: <b>{len(all_grades)}</b>",
    ]

    if last_sync:
        try:
            dt = datetime.fromisoformat(str(last_sync))
            lines.append(f"🕐 Обновлено: <b>{dt.strftime('%d.%m.%Y %H:%M')}</b>")
        except Exception:
            pass

    if cur_term and cur_courses:
        lines.append(f"\n📅 Текущий семестр: <b>{_term_label(cur_term)}</b>")
        lines.append(f"   Предметов: <b>{len(cur_courses)}</b>")
        cur_grades = _collect_grades(cur_courses)
        lines.append(f"   Оценок: <b>{len(cur_grades)}</b>")

    if rec.get("error_msg") and sync_status == "error":
        lines.append(f"\n⚠️ <i>{rec['error_msg'][:200]}</i>")

    lines += [
        "\n📋 <b>Команды:</b>",
        "  /grades   — мои оценки текущего семестра",
        "  /grades 2 — оценки за 2-й семестр",
        "  /stats    — полная статистика",
        "  /subjects — список предметов",
    ]

    await message.answer("\n".join(lines), parse_mode="HTML")
