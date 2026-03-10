"""
Scraper pipeline — 3-phase synchronisation.

Phase 1  ·  INSTITUTES
Phase 2  ·  GROUPS  (Source of Truth)
             Institute → Specialties → Groups
Phase 3  ·  SCHEDULES  (smart diff-sync)
"""
import asyncio
import hashlib
import orjson
import time
from datetime import datetime, date, timedelta
from loguru import logger
import httpx
from tenacity import RetryError

from app.core.config import settings
from app.scraper.client import NCFUClient, get_monday
from app.scraper.parser import (
    parse_institute, parse_group, parse_week, flatten_groups_response,
)
from app.models.institute import Institute
from app.models.group import Group, DaySchedule
from app.models.teacher import Teacher
from app.models.room import Room
from app.models.scrape_log import ScrapeLog
from app.db.database import get_motor_db
from app.cache.redis import invalidate_pattern

# ── configurable thresholds ──────────────────────────────────────────────────
INSTITUTE_TTL_HOURS     = 24
GROUP_TTL_HOURS         = 24
SCHEDULE_TTL_HOURS      = 24
EMPTY_WEEKS_LIMIT       = 4       # check 4-week (1 month) range before stopping
INCREMENTAL_WEEKS       = 3
COOLDOWN_AFTER_FAILURES = 3
COOLDOWN_SECONDS        = 30
CHUNK_SIZE              = 10

_VOLATILE_KEYS = frozenset({"_id", "scraped_at"})


def _canonical_hash(docs: list[dict]) -> str:
    cleaned = [
        {k: v for k, v in sorted(d.items()) if k not in _VOLATILE_KEYS}
        for d in docs
    ]
    return hashlib.md5(
        orjson.dumps(
            cleaned,
            option=orjson.OPT_SORT_KEYS | orjson.OPT_NON_STR_KEYS,
        )
    ).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
class NCFUScraper:

    _BRANCH_IDS = [1, 2, 3]

    def __init__(
        self,
        triggered_by: str = "scheduler",
        mode: str | None = None,
    ) -> None:
        self.triggered_by   = triggered_by
        self.mode           = mode or settings.scrape_mode
        self._sem           = asyncio.Semaphore(settings.scraper_concurrency)
        self._academic_year = (
            f"{settings.academic_year_start}"
                f"-{settings.academic_year_start + 1}"
        )

    # ── entry point ──────────────────────────────────────────────────────────
    async def run(self) -> ScrapeLog:
        log = ScrapeLog(triggered_by=self.triggered_by, mode=self.mode)
        await log.insert()
        t0 = time.monotonic()

        try:
            async with NCFUClient() as client:
                await self._check_connectivity(client)

                await self._phase1_institutes(client)
                groups = await self._phase2_groups(client)
                log.groups_total = len(groups)

                if groups:
                    logger.info(
                        f"Phase 3: schedules [{self.mode}] "
                            f"for {len(groups)} groups"
                    )
                    teachers_acc: dict[int, dict] = {}
                    rooms_acc:    dict[int, dict] = {}
                    await self._phase3_schedules(
                        client, groups, log, teachers_acc, rooms_acc,
                    )
                    logger.info("Phase 4: entity stats")
                    await self._update_entity_stats()
                    logger.info("Phase 5: flush metadata")
                    await self._flush_teachers(teachers_acc)
                    await self._flush_rooms(rooms_acc)
                    log.teachers_upserted = len(teachers_acc)
                    log.rooms_upserted    = len(rooms_acc)
                else:
                    msg = "Phase 2 produced 0 groups — cannot continue"
                    logger.error(msg)
                    log.errors.append(msg)

            await invalidate_pattern("ncfu:*")
            log.status = "success" if not log.errors else "partial"
            logger.info(
                f"Done in {time.monotonic() - t0:.0f}s · "
                    f"scraped={log.groups_scraped} "
                    f"written={log.lessons_written} "
                    f"unchanged={log.lessons_unchanged}"
            )

        except (httpx.ConnectTimeout, httpx.ConnectError,
                httpx.TimeoutException) as exc:
            log.status = "failed"
            log.errors.append(f"Connectivity: {exc}")
            logger.error(f"Connectivity error: {exc}")
        except Exception as exc:
            log.status = "failed"
            log.errors.append(str(exc))
            logger.exception(f"Pipeline failed: {exc}")
        finally:
            log.finished_at = datetime.utcnow()
            await log.save()

        return log

    # ═════════════════════════════════════════════════════════════════════════
    #  Phase 1 — INSTITUTES
    # ═════════════════════════════════════════════════════════════════════════

    async def _phase1_institutes(self, client: NCFUClient) -> None:
        if await self._is_fresh(Institute, INSTITUTE_TTL_HOURS):
            age = await self._stalest_age(Institute)
            logger.info(
                f"Phase 1: fresh ({age:.1f}h < {INSTITUTE_TTL_HOURS}h) "
                    f"— skip"
            )
            return

        logger.info("Phase 1: scraping institutes")
        all_raw: list[Institute] = []
        seen: set[int] = set()

        for bid in self._BRANCH_IDS:
            try:
                async with self._sem:
                    raw = (
                        await client.get_institutes()
                        if bid == 1
                        else await client.get_institutes_for_branch(bid)
                    )
                logger.info(f"   branch {bid}: {len(raw)} institutes")
                for r in raw:
                    if not r or not isinstance(r, dict):
                        continue
                    # parse_institute handles null Id with synthetic IDs
                    inst = parse_institute(r)
                    if inst.institute_id not in seen:
                        seen.add(inst.institute_id)
                        all_raw.append(inst)
            except Exception as exc:
                logger.error(f"   branch {bid} FAILED: {exc}")

        now = datetime.utcnow()
        n   = 0
        for inst in all_raw:
            await Institute.find_one(
                Institute.institute_id == inst.institute_id
            ).upsert(
                {"$set": {
                    "short_name": inst.short_name,
                    "name":       inst.name,
                    "branch_id":  inst.branch_id,
                    "is_synthetic": inst.is_synthetic,
                    "scraped_at": now,
                }},
                on_insert=Institute(
                    institute_id=inst.institute_id,
                    short_name=inst.short_name,
                    name=inst.name,
                    branch_id=inst.branch_id,
                    is_synthetic=inst.is_synthetic,
                    scraped_at=now,
                ),
            )
            n += 1

        logger.info(f"   Phase 1 done: {n} institutes upserted")

    # ═════════════════════════════════════════════════════════════════════════
    #  Phase 2 — GROUPS   (Source of Truth)
    #
    #  The eCampus cascade is:
    #      Institute  →  Specialties  →  Groups
    #
    #  You CANNOT fetch groups directly from an institute ID without
    #  specifying the specialty name.  Passing specialty="" returns [].
    #
    #  Step 2a: for each institute, call get_specialties()
    #  Step 2b: for each specialty, call get_groups(inst, spec_name)
    # ═════════════════════════════════════════════════════════════════════════

    async def _phase2_groups(self, client: NCFUClient) -> list[Group]:
        cnt = await Group.count()
        if cnt > 0 and await self._is_fresh(Group, GROUP_TTL_HOURS):
            age = await self._stalest_age(Group)
            logger.info(
                f"Phase 2: {cnt} groups fresh "
                    f"({age:.1f}h < {GROUP_TTL_HOURS}h) — skip"
            )
            return await Group.find_all().to_list()

        reason = "empty" if cnt == 0 else "stale"
        logger.info(f"Phase 2: scraping groups ({reason})")

        # ── load institutes from DB ────────────────────────────────────────
        institutes = await Institute.find_all().to_list()
        logger.info(f"   loaded {len(institutes)} institutes from DB")
        if not institutes:
            logger.error("   0 institutes — Phase 1 may have failed")
            return await Group.find_all().to_list()

        now             = datetime.utcnow()
        total_upserted  = 0
        total_specs     = 0
        total_raw       = 0
        total_skipped   = 0

        for inst in institutes:
            label = (
                f"{inst.name} (id={inst.institute_id} "
                    f"branch={inst.branch_id})"
            )

            # ── Step 2a: fetch specialties for this institute ──────────────
            try:
                async with self._sem:
                    specs = await client.get_specialties(
                        inst.is_synthetic, inst.institute_id, inst.branch_id,
                    )
            except Exception as exc:
                logger.error(
                    f"   specialties for {label} FAILED: "
                        f"{type(exc).__name__}: {exc}"
                )
                continue

            logger.info(
                f"   {label}: {len(specs)} specialties"
            )
            if not specs:
                continue

            total_specs += len(specs)

            # ── Step 2b: for each specialty, fetch groups ──────────────────
            for spec_name in specs:
                try:
                    async with self._sem:
                        raw_groups = await client.get_groups(
                            inst.institute_id,
                            inst.branch_id,
                            inst.is_synthetic,
                            spec_name,
                        )
                except httpx.HTTPStatusError as exc:
                    logger.error(
                        f"   groups for {label} / {spec_name!r}: "
                            f"HTTP {exc.response.status_code} "
                            f"body={exc.response.text[:200]}"
                    )
                    continue
                except Exception as exc:
                    logger.error(
                        f"   groups for {label} / {spec_name!r}: "
                            f"{type(exc).__name__}: {exc}"
                    )
                    continue

                if not isinstance(raw_groups, list):
                    logger.warning(
                        f"   groups for {label} / {spec_name!r}: "
                            f"expected list, got "
                            f"{type(raw_groups).__name__}: "
                            f"{str(raw_groups)[:200]}"
                    )
                    continue

                # ── Flatten nested Key/Value structure ─────────────────
                flat_groups = flatten_groups_response(raw_groups)
                total_raw += len(flat_groups)

                if flat_groups:
                    logger.info(
                        f"      spec {spec_name!r}: "
                            f"{len(flat_groups)} groups"
                    )

                for rg in flat_groups:
                    grp = parse_group(rg, inst)
                    if grp is None:
                        total_skipped += 1
                        continue

                    try:
                        await Group.find_one(
                            Group.group_id == grp.group_id,
                            Group.source_url == settings.base_url,
                        ).upsert(
                            {"$set": {
                                "name":            grp.name,
                                "source_url":      settings.base_url,
                                "institute_id":    grp.institute_id,
                                "institute_name":  grp.institute_name,
                                "speciality_id":   grp.speciality_id,
                                "speciality_name": grp.speciality_name,
                                "course":          grp.course,
                                "academic_year":   self._academic_year,
                                "scraped_at":      now,
                            }},
                            on_insert=Group(
                                group_id=grp.group_id,
                                name=grp.name,
                                source_url=settings.base_url,
                                institute_id=grp.institute_id,
                                institute_name=grp.institute_name,
                                speciality_id=grp.speciality_id,
                                speciality_name=grp.speciality_name,
                                course=grp.course,
                                academic_year=self._academic_year,
                                scraped_at=now,
                            ),
                        )
                        total_upserted += 1
                    except Exception as exc:
                        logger.error(
                            f"   upsert {grp.name} (id={grp.group_id})"
                                f" FAILED: {type(exc).__name__}: {exc}"
                        )

        logger.info(
            f"   Phase 2 done: specialties={total_specs} "
                f"raw_groups={total_raw} upserted={total_upserted} "
                f"parse_skipped={total_skipped}"
        )

        if total_upserted == 0 and total_raw > 0:
            logger.error(
                f"   Phase 2 BUG: {total_raw} raw entries but "
                    f"0 upserted — check parse_group / upsert logic"
            )
        if total_upserted == 0 and total_raw == 0 and total_specs > 0:
            logger.error(
                f"   Phase 2: {total_specs} specialties found but "
                    f"every get_groups call returned [] — "
                    f"API payload may be wrong"
            )

        return await Group.find_all().to_list()

    # ═════════════════════════════════════════════════════════════════════════
    #  Phase 3 — SCHEDULES
    # ═════════════════════════════════════════════════════════════════════════

    async def _phase3_schedules(
        self, client: NCFUClient, groups: list[Group],
        log: ScrapeLog,
        teachers_acc: dict[int, dict],
        rooms_acc:    dict[int, dict],
    ) -> None:
        total   = len(groups)
        counter = {"done": 0, "scraped": 0, "skipped": 0, "failed": 0}
        fails   = {"streak": 0}

        async def one(group: Group) -> None:
            counter["done"] += 1
            pct = counter["done"] * 100 // total
            pos = f"[{counter['done']}/{total} {pct}%]"

            skip, reason = self._should_skip_schedule(group)
            if skip:
                counter["skipped"] += 1
                log.groups_skipped += 1
                return

            logger.info(f"{pos} {group.name} (id={group.group_id}) — {reason}")

            try:
                result = await self._fetch_group_schedule(
                    client, group.group_id,
                )
                fails["streak"] = 0
                if result is None:
                    logger.info(f"{pos} {group.name}: no data")
                    return

                w, u, ins, upd = await self._flush_lessons_smart(
                    group, result["schedule"],
                )
                log.lessons_written   += w
                log.lessons_unchanged += u

                subjects = sorted({
                    l.subject
                    for day in result["schedule"].values()
                    for l in day.lessons if l.subject
                })
                await Group.find_one(
                    Group.group_id == group.group_id
                ).update({"$set": {
                    "schedule_scraped_at": datetime.utcnow(),
                    "academic_year":       self._academic_year,
                    "scrape_status":       "ok",
                    "lessons_count": sum(
                        len(d.lessons)
                        for d in result["schedule"].values()
                    ),
                    "days_count": len(result["schedule"]),
                    "subjects":   subjects,
                    "schedule":   {},
                }})

                counter["scraped"] += 1
                log.groups_scraped += 1
                self._extract_teachers(
                    teachers_acc, result["schedule"], group,
                )
                self._extract_rooms(
                    rooms_acc, result["schedule"], group,
                )
                logger.info(
                    f"{pos} {group.name} OK "
                        f"days={result['days']} written={w} "
                        f"(ins={ins} upd={upd}) "
                        f"unchanged={u} {result['elapsed']}s"
                )

            except (RetryError, httpx.ConnectTimeout, httpx.ReadTimeout,
                    httpx.ConnectError,
                    httpx.RemoteProtocolError) as exc:
                fails["streak"] += 1
                counter["failed"] += 1
                log.groups_failed += 1
                log.errors.append(
                    f"{group.name}: {type(exc).__name__}"
                )
                logger.warning(
                    f"{pos} {group.name} FAIL "
                        f"{type(exc).__name__} "
                        f"streak={fails['streak']}"
                )
                await Group.find_one(
                    Group.group_id == group.group_id
                ).update({"$set": {"scrape_status": "failed"}})
                if fails["streak"] >= COOLDOWN_AFTER_FAILURES:
                    logger.warning(
                        f"Cooldown {COOLDOWN_SECONDS}s after "
                            f"{fails['streak']} failures"
                    )
                    await asyncio.sleep(COOLDOWN_SECONDS)
                    fails["streak"] = 0

            except Exception as exc:
                counter["failed"] += 1
                log.groups_failed += 1
                log.errors.append(f"{group.name}: {exc}")
                logger.warning(
                    f"{pos} {group.name} FAIL "
                        f"{type(exc).__name__}: {exc}"
                )

        tasks = [one(g) for g in groups]
        for i in range(0, len(tasks), CHUNK_SIZE):
            await asyncio.gather(*tasks[i:i + CHUNK_SIZE])
            await log.save()
            if i + CHUNK_SIZE < len(tasks):
                await asyncio.sleep(1.0)

        logger.info(
            f"Phase 3 done: scraped={counter['scraped']} "
                f"skipped={counter['skipped']} "
                f"failed={counter['failed']}"
        )

    # ── diff-sync ────────────────────────────────────────────────────────────
    async def _flush_lessons_smart(
        self, group: Group, schedule: dict[str, DaySchedule],
    ) -> tuple[int, int, int, int]:
        db  = get_motor_db()
        col = db["lessons"]
        written = unchanged = ins_days = upd_days = 0
        now = datetime.utcnow()

        for iso, day in schedule.items():
            d    = date.fromisoformat(iso)
            d_dt = datetime(d.year, d.month, d.day)

            new_docs = [
                {
                    "date": d_dt,
                    "time_start":     l.time_start,
                    "time_end":       l.time_end,
                    "week_number":    day.week_number,
                    "academic_year":  self._academic_year,
                    "subject":        l.subject,
                    "lesson_type":    l.lesson_type,
                    "subgroup":       l.subgroup,
                    "week_type":      l.week_type,
                    "note":           l.note,
                    "group_id":       group.group_id,
                    "group_name":     group.name,
                    "institute_id":   group.institute_id,
                    "institute_name": group.institute_name,
                    "teacher_id":     l.teacher_id,
                    "teacher_name":   l.teacher_name,
                    "room_id":        l.room_id,
                    "room_name":      l.classroom,
                    "building":       l.building,
                }
                for l in day.lessons
            ]

            existing = await col.find(
                {"date": d_dt, "group_id": group.group_id},
                {"_id": 0, "scraped_at": 0},
            ).to_list(length=None)

            h_new = _canonical_hash(new_docs)
            h_old = _canonical_hash(existing) if existing else ""

            if existing and h_new == h_old:
                unchanged += len(existing)
                continue

            if existing:
                upd_days += 1
            else:
                ins_days += 1

            await col.delete_many(
                {"date": d_dt, "group_id": group.group_id}
            )
            if new_docs:
                for d2 in new_docs:
                    d2["scraped_at"] = now
                await col.insert_many(new_docs)
                written += len(new_docs)

        return written, unchanged, ins_days, upd_days

    # ── schedule freshness ───────────────────────────────────────────────────
    def _should_skip_schedule(
        self, group: Group,
    ) -> tuple[bool, str]:
        if not group.schedule_scraped_at:
            return False, "never scraped"
        age = (
            (datetime.utcnow() - group.schedule_scraped_at)
                .total_seconds() / 3600
        )
        if age > SCHEDULE_TTL_HOURS:
            return False, f"stale ({age:.1f}h)"
        if group.days_count == 0:
            return False, "0 days — retry"
        if group.scrape_status == "failed":
            return False, "prev failed — retry"
        return True, f"fresh ({age:.1f}h, {group.days_count}d)"

    # ── schedule fetch ───────────────────────────────────────────────────────
    async def _fetch_group_schedule(
        self, client: NCFUClient, group_id: int,
    ) -> dict | None:
        t0     = time.monotonic()
        anchor = get_monday(date.today())

        if self.mode == "incremental":
            full: dict = {}
            for i in range(INCREMENTAL_WEEKS):
                mon = anchor + timedelta(weeks=i)
                async with self._sem:
                    raw = await client.get_week_schedule(group_id, mon)
                full.update(parse_week(raw, mon))
            return (
                None if not full else {
                    "schedule": full,
                    "days": len(full),
                    "elapsed": round(time.monotonic() - t0, 2),
                }
            )

        backward: dict = {}
        streak, mon = 0, anchor - timedelta(weeks=1)
        while streak < EMPTY_WEEKS_LIMIT:
            async with self._sem:
                raw = await client.get_week_schedule(group_id, mon)
            wk = parse_week(raw, mon)
            if wk:
                backward.update(wk); streak = 0
            else:
                streak += 1
            mon -= timedelta(weeks=1)

        async with self._sem:
            raw = await client.get_week_schedule(group_id, anchor)
        anchor_wk = parse_week(raw, anchor)

        forward: dict = {}
        streak, mon = 0, anchor + timedelta(weeks=1)
        while streak < EMPTY_WEEKS_LIMIT:
            async with self._sem:
                raw = await client.get_week_schedule(group_id, mon)
            wk = parse_week(raw, mon)
            if wk:
                forward.update(wk); streak = 0
            else:
                streak += 1
            mon += timedelta(weeks=1)

        full = {**backward, **anchor_wk, **forward}
        return (
            None if not full else {
                "schedule": full,
                "days": len(full),
                "elapsed": round(time.monotonic() - t0, 2),
            }
        )

    # ── entity extraction ────────────────────────────────────────────────────
    def _extract_teachers(self, acc, schedule, group):
        for day in schedule.values():
            for l in day.lessons:
                if not l.teacher_id or not l.teacher_name:
                    continue
                if l.teacher_id not in acc:
                    acc[l.teacher_id] = {
                        "teacher_id": l.teacher_id,
                        "full_name": l.teacher_name.strip(),
                        "institute_ids": set(),
                        "institute_names": set(),
                        "subjects": set(), "lesson_types": set(),
                        "group_ids": set(), "group_names": set(),
                    }
                e = acc[l.teacher_id]
                e["institute_ids"].add(group.institute_id)
                e["institute_names"].add(group.institute_name)
                e["group_ids"].add(group.group_id)
                e["group_names"].add(group.name)
                if l.subject:     e["subjects"].add(l.subject)
                if l.lesson_type: e["lesson_types"].add(l.lesson_type)

    def _extract_rooms(self, acc, schedule, group):
        for day in schedule.values():
            for l in day.lessons:
                if not l.room_id or not l.classroom:
                    continue
                if l.room_id not in acc:
                    acc[l.room_id] = {
                        "room_id":    l.room_id,
                        "name":       l.classroom.strip(),
                        "building":   l.building,
                        "source_url": settings.base_url,
                        "subjects": set(), "lesson_types": set(),
                        "group_ids": set(), "group_names": set(),
                        "teacher_ids": set(), "teacher_names": set(),
                        "institute_ids": set(), "institute_names": set(),
                    }
                e = acc[l.room_id]
                e["group_ids"].add(group.group_id)
                e["group_names"].add(group.name)
                e["institute_ids"].add(group.institute_id)
                e["institute_names"].add(group.institute_name)
                if l.subject:      e["subjects"].add(l.subject)
                if l.lesson_type:  e["lesson_types"].add(l.lesson_type)
                if l.teacher_id:   e["teacher_ids"].add(l.teacher_id)
                if l.teacher_name:
                    e["teacher_names"].add(l.teacher_name.strip())

    # ── flush metadata ───────────────────────────────────────────────────────
    async def _flush_teachers(self, teachers):
        now = datetime.utcnow()
        for tid, t in teachers.items():
            doc = {
                "full_name":       t["full_name"],
                "short_name":      Teacher.derive_short_name(t["full_name"]),
                "source_url":      settings.base_url,
                "institute_ids":   sorted(t["institute_ids"]),
                "institute_names": sorted(t["institute_names"]),
                "subjects":        sorted(t["subjects"]),
                "lesson_types":    sorted(t["lesson_types"]),
                "group_ids":       sorted(t["group_ids"]),
                "group_names":     sorted(t["group_names"]),
                "last_seen_at":    now,
            }
            await Teacher.find_one(
                Teacher.teacher_id == tid,
                Teacher.source_url == settings.base_url,
            ).upsert(
                {"$set": doc},
                on_insert=Teacher(teacher_id=tid, **doc),
            )

    async def _flush_rooms(self, rooms):
        now = datetime.utcnow()
        for rid, r in rooms.items():
            doc = {
                "name":            r["name"],
                "building":        r.get("building"),
                "source_url":      settings.base_url,
                "institute_ids":   sorted(r["institute_ids"]),
                "institute_names": sorted(r["institute_names"]),
                "subjects":        sorted(r["subjects"]),
                "lesson_types":    sorted(r["lesson_types"]),
                "group_ids":       sorted(r["group_ids"]),
                "group_names":     sorted(r["group_names"]),
                "teacher_ids":     sorted(r["teacher_ids"]),
                "teacher_names":   sorted(r["teacher_names"]),
                "last_seen_at":    now,
            }
            await Room.find_one(
                Room.room_id == rid,
                Room.source_url == settings.base_url,
            ).upsert(
                {"$set": doc},
                on_insert=Room(room_id=rid, **doc),
            )

    async def _update_entity_stats(self):
        db  = get_motor_db()
        col = db["lessons"]
        now = datetime.utcnow()
        for tid in await col.distinct(
            "teacher_id", {"teacher_id": {"$ne": None}}
        ):
            c = await col.count_documents({"teacher_id": tid})
            e = await Teacher.find_one(Teacher.teacher_id == tid)
            if e:
                await e.update({"$set": {
                    "schedule_scraped_at": now,
                    "scrape_status": "ok",
                    "lessons_count": c,
                }})
        for rid in await col.distinct(
            "room_id", {"room_id": {"$ne": None}}
        ):
            c = await col.count_documents({"room_id": rid})
            e = await Room.find_one(Room.room_id == rid)
            if e:
                await e.update({"$set": {
                    "schedule_scraped_at": now,
                    "scrape_status": "ok",
                    "lessons_count": c,
                }})

    # ── freshness helpers ────────────────────────────────────────────────────
    async def _is_fresh(self, model, ttl_h: float) -> bool:
        if await model.count() == 0:
            return False
        s = await model.find_all().sort("+scraped_at").limit(1).to_list()
        if not s or s[0].scraped_at is None:
            return False
        age = (datetime.utcnow() - s[0].scraped_at).total_seconds() / 3600
        return age < ttl_h

    async def _stalest_age(self, model) -> float:
        s = await model.find_all().sort("+scraped_at").limit(1).to_list()
        if not s or s[0].scraped_at is None:
            return float("inf")
        return (datetime.utcnow() - s[0].scraped_at).total_seconds() / 3600

    async def _check_connectivity(self, client: NCFUClient) -> None:
        async with self._sem:
            await client.get_institutes()
        logger.info("   Connectivity OK")
