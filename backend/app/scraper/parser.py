import re
from datetime import date, datetime
from typing import Any
from loguru import logger

from app.models.group import Group, Lesson, DaySchedule
from app.models.institute import Institute

WEEKDAY_NAMES = {
    0: "Понедельник", 1: "Вторник", 2: "Среда",
    3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье",
}

LESSON_TIMES: dict[int, tuple[str, str]] = {
    1: ("08:00", "09:30"), 2: ("09:40", "11:10"), 3: ("11:20", "12:50"),
    4: ("13:20", "14:50"), 5: ("15:00", "16:30"), 6: ("16:50", "18:20"),
    7: ("18:30", "20:00"), 8: ("20:10", "21:40"),
}


def parse_institute(raw: dict) -> Institute:
    """
    Parse a raw institute dict from the eCampus viewModel.

    Handles null/missing Id: generates a stable synthetic negative ID
    from hash(Name + BranchId) so that subsequent scrapes identify the
    same institute and update it rather than creating duplicates.
    """
    raw_id     = raw.get("Id")
    name       = raw.get("Name") or raw.get("ShortName") or ""
    short_name = raw.get("ShortName") or ""
    branch_id  = raw.get("BranchId") or 1

    if raw_id is not None and raw_id != 0:
        institute_id = int(raw_id)
        is_synthetic = False
    else:
        # Synthetic stable ID: negative hash so it never collides with real IDs
        import hashlib
        key = f"{name.strip().lower()}::{branch_id}"
        institute_id = (
            int(hashlib.md5(key.encode()).hexdigest()[:8], 16) % 900_000
            + 100_000
        )
        is_synthetic = True
        logger.info(
            f"parse_institute: null Id for {name!r} branch={branch_id}, "
            f"synthetic id={institute_id}"
        )

    return Institute(
        institute_id=institute_id,
        short_name=short_name,
        name=name,
        branch_id=branch_id,
        is_synthetic=is_synthetic,
    )


def flatten_groups_response(raw: list | dict | Any) -> list[dict]:
    """
    Flatten the nested GetAcademicGroups response into a flat list of
    group dicts.

    eCampus returns groups grouped by education level:
        [
            {"Key": "Бакалавриат", "Value": [{"Id":123, "Name":"ИСС-б-о-22-3"}, ...]},
            {"Key": "Магистратура", "Value": [{"Id":456, "Name":"ИСС-м-о-24-1"}, ...]},
        ]

    We need to iterate the outer list, pull out .Value from each entry,
    and merge everything into a single flat list of group dicts.

    Also handles the simpler case where the response is already a flat
    list of group dicts (forward compatibility).
    """
    if not raw:
        return []

    # If it's already a flat list of group dicts, return as-is
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        # Check if this is a flat list (items have "Id"/"Name")
        # or a nested list (items have "Key"/"Value")
        first = raw[0]
        if "Value" in first and isinstance(first.get("Value"), list):
            # Nested structure: flatten
            flat: list[dict] = []
            for level in raw:
                if not isinstance(level, dict):
                    logger.warning(
                        f"flatten_groups: expected dict in outer list, "
                        f"got {type(level).__name__}: {str(level)[:100]}"
                    )
                    continue
                level_name = level.get("Key", "?")
                groups = level.get("Value")
                if not isinstance(groups, list):
                    logger.warning(
                        f"flatten_groups: 'Value' for level {level_name!r} "
                        f"is not a list: {type(groups).__name__}"
                    )
                    continue
                for g in groups:
                    if isinstance(g, dict):
                        flat.append(g)
                    else:
                        logger.warning(
                            f"flatten_groups: non-dict in Value for "
                            f"{level_name!r}: {type(g).__name__}"
                        )
            if flat:
                logger.debug(
                    f"flatten_groups: flattened {len(raw)} levels → "
                    f"{len(flat)} groups"
                )
            return flat
        else:
            # Already flat
            return raw

    if isinstance(raw, dict):
        # Maybe the whole thing is wrapped: {"Groups": [...]}
        for key in ("Groups", "Items", "Data", "Value"):
            if key in raw and isinstance(raw[key], list):
                return flatten_groups_response(raw[key])

    logger.warning(
        f"flatten_groups: unexpected structure "
        f"{type(raw).__name__}: {str(raw)[:200]}"
    )
    return []


def parse_group(raw: dict, inst: Institute) -> Group | None:
    group_id = raw.get("Id")
    name     = raw.get("Name", "")

    if group_id is None:
        logger.warning(
            f"parse_group: no 'Id' key. "
            f"keys={list(raw.keys())} entry={str(raw)[:300]}"
        )
        return None
    if not name:
        logger.warning(
            f"parse_group: empty Name for Id={group_id}"
        )
        return None

    course: int | None = None
    m = re.search(r"-(\d{2})-\d+\s*$", name)
    if m:
        enrol_year = 2000 + int(m.group(1))
        today = date.today()
        ays = today.year if today.month >= 9 else today.year - 1
        course = ays - enrol_year + 1
        if not (1 <= course <= 7):
            course = None

    try:
        return Group(
            group_id=int(group_id),
            name=name,
            institute_id=inst.institute_id,
            institute_name=inst.name,
            speciality_id=raw.get("SpecialityId"),
            speciality_name=raw.get("SpecialityName"),
            course=course,
        )
    except Exception as exc:
        logger.error(
            f"parse_group: model build failed for "
            f"Id={group_id} Name={name!r} — "
            f"{type(exc).__name__}: {exc}"
        )
        return None


def parse_week(raw: Any, monday: date) -> dict[str, DaySchedule]:
    if not raw:
        return {}
    days_raw: list[dict] = []
    if isinstance(raw, list):
        days_raw = raw
    elif isinstance(raw, dict):
        for key in ("Days", "Schedule", "Items", "Data"):
            if key in raw and isinstance(raw[key], list):
                days_raw = raw[key]
                break
    if not days_raw:
        return {}

    result: dict[str, DaySchedule] = {}
    for day_raw in days_raw:
        try:
            d = _parse_date(day_raw.get("Date") or day_raw.get("Day", ""))
            if not d:
                continue
            lessons_raw = day_raw.get("Lessons") or day_raw.get("Items", [])
            lessons = [l for lr in lessons_raw if (l := _parse_lesson(lr))]
            if not lessons:
                continue
            wd = d.weekday()
            result[d.isoformat()] = DaySchedule(
                weekday=wd,
                weekday_name=WEEKDAY_NAMES.get(wd, ""),
                week_number=d.isocalendar().week,
                lessons=sorted(lessons, key=lambda l: l.lesson_number),
            )
        except Exception as exc:
            logger.warning(f"Skipping malformed day: {exc}")
    return result


def _parse_lesson(raw: dict) -> Lesson | None:
    try:
        num = int(
            raw.get("PairNumberStart") or raw.get("Number") or
            raw.get("LessonNumber") or raw.get("Order") or 0
        )
        times = LESSON_TIMES.get(num, ("??:??", "??:??"))

        def hhmm(v):
            if not v:
                return "??:??"
            s = str(v)
            return s.split("T")[1][:5] if "T" in s else s[:5]

        t_raw = raw.get("TeacherName") or raw.get("Teacher") or raw.get("Lecturer")
        teacher = (t_raw.get("Name") if isinstance(t_raw, dict) else t_raw or "").strip() or None

        a_raw = raw.get("Aud") or raw.get("Classroom") or raw.get("RoomName") or raw.get("Room")
        classroom = (a_raw.get("Name") if isinstance(a_raw, dict) else a_raw or "").strip() or None

        subject = (raw.get("Discipline") or raw.get("SubjectName") or raw.get("Subject") or "").strip()

        lt_raw = raw.get("LessonType") or raw.get("LessonTypeName") or raw.get("TypeName") or ""
        lesson_type = lt_raw.strip() if isinstance(lt_raw, str) else None

        subgroup = None
        for sg_field in (raw.get("SubGroups") or raw.get("Groups") or []):
            sg = sg_field.get("Subgroup") or sg_field.get("SubGroup")
            if sg:
                subgroup = str(sg).strip()
                break
        if not subgroup:
            sg = raw.get("SubGroup") or raw.get("Subgroup")
            subgroup = str(sg).strip() if sg else None

        teacher_id = raw.get("TeacherId")
        room_id    = raw.get("RoomId")

        building = raw.get("Building") or raw.get("BuildingName")
        if not building and classroom:
            m = re.match(r"^([А-ЯA-Z]{1,3}|\d+)-", classroom)
            if m:
                building = f"Корпус {m.group(1)}"

        wt = raw.get("WeekType") or raw.get("Parity") or "all"
        week_type = {0: "all", 1: "odd", 2: "even"}.get(wt, str(wt).lower()) if isinstance(wt, int) else str(wt).lower()

        return Lesson(
            lesson_number=num,
            time_start=hhmm(raw.get("TimeBegin") or raw.get("TimeStart") or times[0]),
            time_end=hhmm(raw.get("TimeEnd") or times[1]),
            subject=subject,
            lesson_type=lesson_type or None,
            teacher_id=int(teacher_id) if teacher_id else None,
            teacher_name=teacher,
            room_id=int(room_id) if room_id else None,
            classroom=classroom,
            building=building,
            subgroup=subgroup,
            week_type=week_type,
            note=raw.get("Note"),
        )
    except Exception as exc:
        logger.warning(f"Could not parse lesson: {exc}")
        return None


def _parse_date(raw: str) -> date | None:
    if not raw:
        return None
    if raw.startswith("/Date("):
        import re as _re
        ms = int(_re.search(r"\d+", raw).group())
        return datetime.utcfromtimestamp(ms / 1000).date()
    clean = raw.split("+")[0].rstrip("Z").strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue
    logger.warning(f"Cannot parse date: {raw!r}")
    return None
