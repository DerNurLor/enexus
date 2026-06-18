import strawberry
from typing import Optional, List


# ── Lesson ────────────────────────────────────────────────────────────────────

@strawberry.type
class LessonType:
    date:          str
    time_start:    str
    time_end:      str
    week_number:   int
    academic_year: str
    subject:       str
    lesson_type:   Optional[str]
    subgroup:      Optional[str]
    week_type:     Optional[str]
    note:          Optional[str]
    # Group context
    group_id:      int
    group_name:    str
    institute_id:  Optional[int]
    institute_name: Optional[str]
    # Teacher context
    teacher_id:    Optional[int]
    teacher_name:  Optional[str]
    # Room context
    room_id:       Optional[int]
    room_name:     Optional[str]
    building:      Optional[str]


@strawberry.type
class DayType:
    date:         str
    weekday:      int
    weekday_name: str
    week_number:  int
    lessons:      List[LessonType]


# ── Paginator ─────────────────────────────────────────────────────────────────

@strawberry.type
class PageInfo:
    has_next_page: bool
    end_cursor:    Optional[str]
    total_count:   int


# ── Institute ─────────────────────────────────────────────────────────────────

@strawberry.type
class InstituteType:
    institute_id: int
    short_name:   str
    name:         str
    branch_id:    int
    groups_count: int


# ── Group ─────────────────────────────────────────────────────────────────────

@strawberry.type
class GroupType:
    group_id:        int
    name:            str
    institute_id:    int
    institute_name:  str
    speciality_name: Optional[str]
    course:          Optional[int]
    academic_year:   Optional[str]
    subjects:        List[str]
    lessons_count:   int
    days_count:      int
    scrape_status:   str
    schedule_scraped_at: Optional[str]


@strawberry.type
class GroupConnection:
    nodes:     List[GroupType]
    page_info: PageInfo


# ── Teacher ───────────────────────────────────────────────────────────────────

@strawberry.type
class TeacherType:
    teacher_id:      int
    full_name:       str
    short_name:      Optional[str]
    institute_ids:   List[int]
    institute_names: List[str]
    subjects:        List[str]
    lesson_types:    List[str]
    group_names:     List[str]
    lessons_count:   int
    scrape_status:   str
    schedule_scraped_at: Optional[str]


@strawberry.type
class TeacherConnection:
    nodes:     List[TeacherType]
    page_info: PageInfo


# ── Room ──────────────────────────────────────────────────────────────────────

@strawberry.type
class RoomType:
    room_id:       int
    name:          str
    building:      Optional[str]
    capacity:      Optional[int]
    subjects:      List[str]
    teacher_names: List[str]
    group_names:   List[str]
    lessons_count: int
    scrape_status: str
    schedule_scraped_at: Optional[str]


@strawberry.type
class RoomConnection:
    nodes:     List[RoomType]
    page_info: PageInfo


# ── Free rooms ────────────────────────────────────────────────────────────────

@strawberry.type
class FreeRoomType:
    room_id:  int
    name:     str
    building: Optional[str]
    capacity: Optional[int]


# ── Connections ───────────────────────────────────────────────────────────────

@strawberry.type
class LessonConnection:
    nodes:     List[LessonType]
    page_info: PageInfo


# ── Search ────────────────────────────────────────────────────────────────────

@strawberry.type
class SearchResult:
    groups:     List[GroupType]
    teachers:   List[TeacherType]
    rooms:      List[RoomType]
    data_as_of: str


# ── Overview ──────────────────────────────────────────────────────────────────

@strawberry.type
class ScrapeLogSummary:
    id:                str
    started_at:        str
    finished_at:       Optional[str]
    status:            str
    mode:              str
    groups_total:      int
    groups_scraped:    int
    groups_failed:     int
    lessons_written:   int
    lessons_unchanged: int
    teachers_upserted: int
    rooms_upserted:    int
    errors:            List[str]
    triggered_by:      str
    duration_seconds:  Optional[float]


@strawberry.type
class InstituteStats:
    institute_id:   int
    institute_name: str
    short_name:     str
    groups_count:   int
    teachers_count: int
    lessons_count:  int


@strawberry.type
class SubjectStats:
    subject:       str
    lessons_count: int
    groups_count:  int
    teachers_count: int


@strawberry.type
class DayLoadStats:
    date:          str
    weekday_name:  str
    lessons_count: int
    groups_active: int


@strawberry.type
class OverviewType:
    # Totals
    groups_total:   int
    teachers_total: int
    rooms_total:    int
    lessons_total:  int
    institutes_total: int
    # Scrape health
    last_scrape_at:       Optional[str]
    last_scrape_status:   Optional[str]
    last_scrape_mode:     Optional[str]
    last_scrape_duration: Optional[float]
    lessons_written_last: Optional[int]
    groups_failed_last:   Optional[int]
    # Recent logs
    recent_scrapes:      List[ScrapeLogSummary]
    # Breakdown by institute
    by_institute:        List[InstituteStats]
    # Top subjects
    top_subjects:        List[SubjectStats]
    # Upcoming week load
    upcoming_days:       List[DayLoadStats]
    data_as_of:          str


# ── Mutation result ───────────────────────────────────────────────────────────

@strawberry.type
class ScrapeResultType:
    status:       str
    mode:         str
    triggered_at: str


# ── Subscription event ────────────────────────────────────────────────────────

@strawberry.type
class ScheduleUpdatedEvent:
    group_id:      int
    group_name:    str
    changed_dates: List[str]
    data_as_of:    str


# ── eCampus (per-student data) ─────────────────────────────────────────────────
# Курс отдаётся БЕЗ сырых занятий (lessons) — это та самая тяжёлая часть,
# из-за которой REST GET /ecampus/data грузился 1-2 минуты. Рейтинг считается
# на сервере (где данные уже лежат в Mongo) и отдаётся готовым числом.
# gradedLessons — компактный список {id, gradeText} только для занятий с
# оценкой (нужен фронту для подсчёта "новых оценок" — см. updateGradeSnapshot).

@strawberry.type
class EcampusLessonTypeRefType:
    id:          int
    name:        str
    # int, не str: eCampus LessonType — числовой код (1, 3, 4, 5, 6, 12…), на
    # фронте сравнивается с Set<number> (EXAM_TYPES/CREDIT_TYPES/COURSE_WORK_TYPES
    # в web/app/ecampus/page.tsx). Был объявлен как str — GraphQL сериализовал
    # его в "4" вместо 4, и Set<number>.has("4") всегда возвращал false, поэтому
    # фильтры по типу занятия (экзамен/зачёт/курсовая) никогда не срабатывали.
    lesson_type: Optional[int]


@strawberry.type
class EcampusGradedLessonType:
    # str, не int: eCampus lesson Id — сквозной ID занятия по всему универу,
    # превышает 32-битный диапазон GraphQL Int (напр. 2256343093) и ломал
    # сериализацию всего ответа. Фронт использует его только как ключ
    # (updateGradeSnapshot), числовое значение не нужно.
    id:         str
    grade_text: str


@strawberry.type
class EcampusCourseType:
    id:             int
    name:           str
    term_id:        int
    term_name:      str
    lesson_types:   List[EcampusLessonTypeRefType]
    rating_gained:  float
    rating_max:     float
    graded_lessons: List[EcampusGradedLessonType]


@strawberry.type
class EcampusOverviewType:
    sync_status: str
    last_sync:   Optional[str]
    courses:     List[EcampusCourseType]
    # Зачётка отдаётся как есть (JSON) — её форма фиксированной глубины и не
    # участвует в проблеме производительности, поэтому не типизируем строго.
    zachetka:    strawberry.scalars.JSON


@strawberry.type
class EcampusYearType:
    """Метаданные одного учебного года — для распараллеливания myEcampus по году на фронте."""
    year:          str
    term_ids:      List[int]
    course_count:  int


@strawberry.type
class EcampusCourseLessonsType:
    course_id:      int
    course_name:    str
    # Сырые занятия — нужны целиком только при открытии конкретного курса,
    # форма не фиксирована (поля разнятся), поэтому JSON, как и zachetka.
    lessons:        strawberry.scalars.JSON
    max_rating:     float
    current_rating: float


@strawberry.type
class EcampusMaterialType:
    label:    str
    url:      str
    icon:     str
    external: bool
    color:    str

