"""
All intent models in one file.
Instructor extracts one of these from any Russian message.
"""
from __future__ import annotations
from typing import Annotated, Literal, Optional, Union
from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────────────────

class TimeRef(BaseModel):
    """Resolved or relative time reference extracted from the message."""
    iso: Optional[str] = Field(None, description="Exact ISO datetime if user said explicit date+time, e.g. '2026-03-10T14:00'")
    offset_minutes: Optional[int] = Field(None, description="Offset from now in minutes, e.g. 5, -10. Use only for short relative times like 'через 5 минут'")
    date_expr: Optional[str] = Field(
        None,
        description=(
            "Natural language date expression when user refers to a day. "
            "Use one of: 'today', 'tomorrow', 'day_after_tomorrow', "
            "'next_week', 'monday', 'tuesday', 'wednesday', 'thursday', "
            "'friday', 'saturday', 'sunday', 'next_monday', 'next_tuesday', "
            "'next_wednesday', 'next_thursday', 'next_friday', 'next_saturday', 'next_sunday', "
            "or an ISO date string 'YYYY-MM-DD'."
        )
    )
    time_of_day: Optional[str] = Field(
        None,
        description="HH:MM time of day if user specified one, e.g. '14:00', '9:30'. If omitted, defaults to start of working day (08:00)."
    )


# ── Intent models ─────────────────────────────────────────────────────────────

class GroupScheduleIntent(BaseModel):
    """User wants the schedule for a specific group."""
    intent: Literal["group_schedule"] = "group_schedule"
    group_name: Optional[str] = Field(None, description="Group name, e.g. 'ИСС-б-о-22-3'")
    group_id: Optional[int] = Field(None, description="Numeric group ID if known")
    from_date: Optional[str] = Field(None, description="Start date ISO YYYY-MM-DD")
    to_date: Optional[str] = Field(None, description="End date ISO YYYY-MM-DD")
    week: Optional[int] = Field(None, description="ISO week number")


class TeacherScheduleIntent(BaseModel):
    """User wants the schedule for a specific teacher."""
    intent: Literal["teacher_schedule"] = "teacher_schedule"
    teacher_name: str = Field(
        description=(
            "Teacher full name or surname, copied verbatim from user's message. "
            "Do NOT convert grammatical case — pass the exact form the user wrote. "
            "Examples: 'Щербина', 'Щербины', 'Безпалько', 'Иванов И.И.', 'Подзолко'. "
            "The backend handles case normalization."
        )
    )
    from_date: Optional[str] = Field(None, description="Start date ISO YYYY-MM-DD")
    to_date: Optional[str] = Field(None, description="End date ISO YYYY-MM-DD")
    week: Optional[int] = Field(None, description="ISO week number")


class TeacherNowIntent(BaseModel):
    """User asks where a teacher is right now or in N minutes."""
    intent: Literal["teacher_now"] = "teacher_now"
    teacher_name: str = Field(description="Teacher surname or full name")
    time_ref: Optional[TimeRef] = Field(None, description="Time offset if 'через X минут'")


class GroupNowIntent(BaseModel):
    """User asks what lesson a group has right now or in N minutes."""
    intent: Literal["group_now"] = "group_now"
    group_name: str = Field(description="Group name")
    time_ref: Optional[TimeRef] = Field(None, description="Time offset if 'через X минут'")


class FreeRoomsIntent(BaseModel):
    """User asks which rooms are free right now or at a specific time."""
    intent: Literal["free_rooms"] = "free_rooms"
    building: Optional[str] = Field(None, description="Building name or number, e.g. 'корпус 1', '2 корпус', '11'")
    time_ref: Optional[TimeRef] = Field(None, description="When to check; None means now")
    duration_minutes: int = Field(90, description="How long the room is needed, default 90 min")


class BuildingScheduleIntent(BaseModel):
    """User asks WHEN rooms in a building are free (not at a specific time).
    Examples: 'когда свободны аудитории в 11 корпусе', 'в какое время завтра свободен корпус 3'."""
    intent: Literal["building_schedule"] = "building_schedule"
    building: str = Field(description="Building number or name, e.g. '11', 'корпус 3'")
    time_ref: Optional[TimeRef] = Field(None, description="Date reference if not today, e.g. 'tomorrow', 'next_monday'")


class RoomScheduleIntent(BaseModel):
    """User wants the schedule for a specific room/auditorium."""
    intent: Literal["room_schedule"] = "room_schedule"
    room_name: Optional[str] = Field(
        None,
        description=(
            "Room/auditorium name or number. Preserve the full format as user wrote it. "
            "Examples: '405', '11-405', '11-216', '11-310', 'ауд. 216'. "
            "If user says 'корпус 11 аудитория 405' or '11 корпус 405' → use '11-405'. "
            "If user says just '405' without building → use '405'. "
            "For gym/sport hall: if user says 'спортзал' → use 'спортзал'; "
            "'9 спортзал' or '9 с/з' or 'спортзал 9 корпуса' → use '9-спортзал'; "
            "'с/з' or 'сз' → use 'с/з'. Always preserve building prefix if mentioned."
        )
    )
    room_id: Optional[int] = Field(None)
    from_date: Optional[str] = None
    to_date: Optional[str] = None


class SearchIntent(BaseModel):
    """User is searching for a group, teacher or room by name."""
    intent: Literal["search"] = "search"
    query: str = Field(description="The search query extracted from the message")
    institute_name: Optional[str] = Field(None, description="Institute filter if mentioned")


class LessonsOnDayIntent(BaseModel):
    """User wants all lessons on a specific date, optionally filtered."""
    intent: Literal["lessons_on_day"] = "lessons_on_day"
    day: str = Field(description="ISO date YYYY-MM-DD")
    group_name: Optional[str] = None
    teacher_name: Optional[str] = None
    room_name: Optional[str] = None
    institute_name: Optional[str] = None
    subject: Optional[str] = None


class OverviewIntent(BaseModel):
    """User asks for general stats or overview of the system."""
    intent: Literal["overview"] = "overview"


class InstitutesIntent(BaseModel):
    """User asks for a list of institutes/faculties."""
    intent: Literal["institutes"] = "institutes"
    query: Optional[str] = Field(None, description="Filter query if user named a specific institute")


class UnknownIntent(BaseModel):
    """Could not determine a specific intent."""
    intent: Literal["unknown"] = "unknown"
    clarification_needed: str = Field(description="Short question to ask the user for clarification")


# ── Union type used by Instructor ─────────────────────────────────────────────

AnyIntent = Annotated[
    Union[
        GroupScheduleIntent,
        TeacherScheduleIntent,
        TeacherNowIntent,
        GroupNowIntent,
        FreeRoomsIntent,
        BuildingScheduleIntent,
        RoomScheduleIntent,
        SearchIntent,
        LessonsOnDayIntent,
        OverviewIntent,
        InstitutesIntent,
        UnknownIntent,
    ],
    Field(discriminator="intent"),
]


class IntentResponse(BaseModel):
    """Top-level response from the LLM."""
    result: AnyIntent
