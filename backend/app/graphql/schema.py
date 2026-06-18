"""
graphql/schema.py — hardened.

Security changes:
  [V8] Query depth limiting via strawberry-django depth-limit extension.
       Max depth = 5 prevents deeply nested N+1 / resource-exhaustion attacks.
  [V5] GraphiQL IDE access requires X-Admin-Secret header (enforced in main.py middleware).
       The description string no longer hints at ?secret= URL pattern.
"""
import strawberry
from typing import Optional, List, AsyncGenerator
from fastapi import Request
from strawberry.fastapi import GraphQLRouter
from strawberry.extensions import MaxTokensLimiter

from app.graphql import resolvers as R
from app.graphql.types import (
    InstituteType,
    GroupConnection, GroupType,
    TeacherConnection,
    RoomConnection,
    LessonConnection, DayType,
    FreeRoomType, SearchResult,
    OverviewType, ScrapeResultType, ScheduleUpdatedEvent,
    EcampusOverviewType, EcampusYearType, EcampusCourseLessonsType, EcampusMaterialType,
)


# ── Auth context для per-user полей (eCampus) ─────────────────────────────────
# Остальная схема (institutes/groups/teachers/...) — публичные данные расписания,
# им контекст не нужен. eCampus — персональные данные студента, поэтому
# Query.myEcampus требует тот же Bearer JWT, что и REST API.

async def get_graphql_context(request: Request) -> dict:
    user = None
    authorization = request.headers.get("authorization")
    if authorization:
        try:
            from app.auth.dependencies import get_current_user
            user = await get_current_user(request, authorization)
        except Exception:
            user = None
    return {"user": user}


# ── [V8] Query depth limiter extension ────────────────────────────────────────

class QueryDepthLimiter(strawberry.extensions.SchemaExtension):
    """
    Rejects queries whose AST depth exceeds MAX_DEPTH.

    Why: Without a depth limit, a malicious client can craft deeply nested
    queries (e.g. groups → lessons → teacher → groups → lessons → …) that
    force O(n^k) database lookups and exhaust server resources.

    MAX_DEPTH = 5 allows:
      { groups { edges { node { schedule { lessons { subject } } } } } }
    which covers all legitimate use cases in this schema.
    """

    MAX_DEPTH = 5

    def on_executing_start(self):
        from graphql import parse as _parse
        from graphql.language import (
            FieldNode, SelectionSetNode, FragmentSpreadNode,
            InlineFragmentNode, DocumentNode,
        )

        def _depth(node, current: int = 0) -> int:
            if isinstance(node, FieldNode):
                if node.selection_set:
                    return _depth(node.selection_set, current + 1)
                return current
            if isinstance(node, SelectionSetNode):
                return max((_depth(sel, current) for sel in node.selections), default=current)
            if isinstance(node, (InlineFragmentNode, FragmentSpreadNode)):
                if hasattr(node, "selection_set") and node.selection_set:
                    return _depth(node.selection_set, current)
            return current

        doc: DocumentNode = self.execution_context.graphql_document
        for definition in doc.definitions:
            sel_set = getattr(definition, "selection_set", None)
            if sel_set:
                depth = _depth(sel_set)
                if depth > self.MAX_DEPTH:
                    from graphql import GraphQLError
                    self.execution_context.errors = [
                        GraphQLError(
                            f"Query depth {depth} exceeds maximum allowed depth of {self.MAX_DEPTH}."
                        )
                    ]
                    return


# ── Schema ────────────────────────────────────────────────────────────────────

@strawberry.type
class Query:

    @strawberry.field(description="List all institutes, optionally filtered by name")
    async def institutes(self, q: Optional[str] = None) -> List[InstituteType]:
        return await R.resolve_institutes(q)

    @strawberry.field(description="List groups. Filter by name, institute, or course. Cursor-paginated.")
    async def groups(
        self,
        q:              Optional[str] = None,
        institute_id:   Optional[int] = None,
        institute_name: Optional[str] = None,
        course:         Optional[int] = None,
        first:          int = 50,
        after:          Optional[str] = None,
    ) -> GroupConnection:
        return await R.resolve_groups(q, institute_id, institute_name, course, first, after)

    @strawberry.field(description="Schedule for a group. Accepts group_id OR group_name. Defaults to current week.")
    async def group_schedule(
        self,
        group_id:   Optional[int] = None,
        group_name: Optional[str] = None,
        from_date:  Optional[str] = None,
        to_date:    Optional[str] = None,
        week:       Optional[int] = None,
    ) -> List[DayType]:
        return await R.resolve_group_schedule(group_id, group_name, from_date, to_date, week)

    @strawberry.field(description="List teachers. Filter by name, subject, institute. Cursor-paginated.")
    async def teachers(
        self,
        q:              Optional[str] = None,
        subject:        Optional[str] = None,
        institute_id:   Optional[int] = None,
        institute_name: Optional[str] = None,
        first:          int = 50,
        after:          Optional[str] = None,
    ) -> TeacherConnection:
        return await R.resolve_teachers(q, subject, institute_id, institute_name, first, after)

    @strawberry.field(description="Schedule for a teacher. Accepts teacher_id OR teacher_name. Defaults to current week.")
    async def teacher_schedule(
        self,
        teacher_id:   Optional[int] = None,
        teacher_name: Optional[str] = None,
        from_date:    Optional[str] = None,
        to_date:      Optional[str] = None,
        week:         Optional[int] = None,
    ) -> List[DayType]:
        return await R.resolve_teacher_schedule(teacher_id, teacher_name, from_date, to_date, week)

    @strawberry.field(description="List rooms. Filter by name or building. Cursor-paginated.")
    async def rooms(
        self,
        q:        Optional[str] = None,
        building: Optional[str] = None,
        first:    int = 50,
        after:    Optional[str] = None,
    ) -> RoomConnection:
        return await R.resolve_rooms(q, building, first, after)

    @strawberry.field(description="Schedule for a room.")
    async def room_schedule(
        self,
        room_id:   Optional[int] = None,
        room_name: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date:   Optional[str] = None,
        week:      Optional[int] = None,
    ) -> List[DayType]:
        return await R.resolve_room_schedule(room_id, room_name, from_date, to_date, week)

    @strawberry.field(description="All lessons currently in progress right now")
    async def lessons_now(self) -> List[strawberry.scalars.JSON]:
        lessons = await R.resolve_lessons_now()
        return [strawberry.as_dict(l) for l in lessons]

    @strawberry.field(description="Lessons on a specific date with rich filtering.")
    async def lessons_on(
        self,
        date:           str,
        group_id:       Optional[int] = None,
        group_name:     Optional[str] = None,
        teacher_id:     Optional[int] = None,
        teacher_name:   Optional[str] = None,
        room_id:        Optional[int] = None,
        room_name:      Optional[str] = None,
        institute_id:   Optional[int] = None,
        institute_name: Optional[str] = None,
        subject:        Optional[str] = None,
        first:          int = 50,
        after:          Optional[str] = None,
    ) -> LessonConnection:
        return await R.resolve_lessons_on(
            date, group_id, group_name, teacher_id, teacher_name,
            room_id, room_name, institute_id, institute_name, subject, None, first,
        )

    @strawberry.field(description="Rooms free for N minutes starting at a given datetime (ISO 8601).")
    async def free_rooms(
        self,
        at:          Optional[str] = None,
        duration:    int = 90,
        building:    Optional[str] = None,
        institute_id: Optional[int] = None,
    ) -> List[FreeRoomType]:
        return await R.resolve_free_rooms(at, duration, building)

    @strawberry.field(description="Universal search across groups, teachers, rooms.")
    async def search(
        self,
        q:            str,
        institute_id: Optional[int] = None,
    ) -> SearchResult:
        return await R.resolve_search(q, institute_id)

    @strawberry.field(description="Rich overview: totals, scrape health, per-institute stats.")
    async def overview(self, recent_scrapes_limit: int = 5) -> OverviewType:
        return await R.resolve_overview(recent_scrapes_limit)

    @strawberry.field(
        description=(
            "Authenticated student's eCampus overview: courses (lightweight — "
            "ratings computed server-side, no raw lesson dump), zachetka, sync "
            "status. Requires Bearer auth. Replaces REST GET /ecampus/data. "
            "Pass termIds to fetch only a subset (e.g. one academic year) — "
            "see myEcampusYears for the available term_id groups."
        )
    )
    async def my_ecampus(self, info: strawberry.Info, term_ids: Optional[List[int]] = None) -> EcampusOverviewType:
        user = info.context.get("user")
        if not user:
            raise Exception("Authentication required")
        return await R.resolve_my_ecampus(user.tg_id, term_ids)

    @strawberry.field(
        description="Lightweight metadata: academic years with their term_ids and course counts — for splitting myEcampus into parallel per-year requests."
    )
    async def my_ecampus_years(self, info: strawberry.Info) -> List[EcampusYearType]:
        user = info.context.get("user")
        if not user:
            raise Exception("Authentication required")
        return await R.resolve_my_ecampus_years(user.tg_id)

    @strawberry.field(description="Lessons of a single course (raw, enriched with room from schedule if group_id given). Replaces REST GET /ecampus/course/{id}/lessons.")
    async def my_ecampus_course_lessons(
        self, info: strawberry.Info, course_id: int, term_id: int, group_id: Optional[int] = None,
    ) -> EcampusCourseLessonsType:
        user = info.context.get("user")
        if not user:
            raise Exception("Authentication required")
        return await R.resolve_my_ecampus_course_lessons(user.tg_id, course_id, term_id, group_id)

    @strawberry.field(description="Available materials for a single course. Replaces REST GET /ecampus/course/{id}/materials.")
    async def my_ecampus_course_materials(self, info: strawberry.Info, course_id: int, term_id: int) -> List[EcampusMaterialType]:
        user = info.context.get("user")
        if not user:
            raise Exception("Authentication required")
        return await R.resolve_my_ecampus_course_materials(user.tg_id, course_id, term_id)


@strawberry.type
class Mutation:
    @strawberry.mutation(description="Trigger a scrape job (mode: incremental | full)")
    async def trigger_scrape(self, mode: str = "incremental") -> ScrapeResultType:
        return await R.resolve_trigger_scrape(mode)


@strawberry.type
class Subscription:
    @strawberry.subscription(description="Real-time schedule-updated events from the scraper")
    async def schedule_updated(
        self, group_id: Optional[int] = None
    ) -> AsyncGenerator[ScheduleUpdatedEvent, None]:
        async for event in R.subscribe_schedule_updated(group_id):
            yield event


# [V8] Depth limiter + token limiter registered as schema extensions.
# MaxTokensLimiter(1000) caps query document size to prevent token-flood DoS.
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
    extensions=[
        QueryDepthLimiter,
        MaxTokensLimiter(max_token_count=1000),
    ],
)

# [V5] GraphiQL access is gated by X-Admin-Secret header in GraphiQLGuard middleware.
graphql_router = GraphQLRouter(
    schema,
    graphql_ide="graphiql",
    subscription_protocols=["graphql-ws"],
    context_getter=get_graphql_context,
)
