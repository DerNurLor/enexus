#!/usr/bin/env python3
"""
migrate_institute_ids.py
────────────────────────
Backfills `institute_ids` and `institute_names` on:
  - rooms      (Room collection)
  - teachers   (Teacher collection)

Стратегия получения данных (два источника, combined):
  1. LessonDoc.institute_id/institute_name — наиболее точно, но может быть NULL
     у старых записей.
  2. Фоллбек через Group — Group.group_id → Group.institute_id/name.
     Если LessonDoc.institute_id = NULL, используем institute_id группы из lesson.

Usage:
    cd backend
    python scripts/migrate_institute_ids.py            # применить
    python scripts/migrate_institute_ids.py --dry-run  # проверить без записи

Requires MONGO_URL env var (or .env file at project root).
"""
import asyncio
import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.models.room    import Room
from app.models.teacher import Teacher
from app.models.group   import Group
from app.models.lesson  import LessonDoc


async def build_group_institute_map() -> dict[int, tuple[int, str]]:
    """
    Строим маппинг group_id → (institute_id, institute_name) из коллекции groups.
    Используется как фоллбек когда в LessonDoc нет institute_id.
    """
    print("Building group→institute map from groups collection …")
    mapping: dict[int, tuple[int, str]] = {}
    async for group in Group.find_all():
        if group.institute_id and group.institute_name:
            mapping[group.group_id] = (group.institute_id, group.institute_name)
    print(f"  Groups with institute data: {len(mapping)}")
    return mapping


async def build_institute_maps(
    group_inst_map: dict[int, tuple[int, str]]
) -> tuple[dict[int, dict[int, str]], dict[int, dict[int, str]]]:
    """
    Сканируем LessonDoc и строим два маппинга:
        room_id    → {institute_id: institute_name, ...}
        teacher_id → {institute_id: institute_name, ...}

    Если institute_id у урока отсутствует — используем фоллбек через group_id.
    """
    print("\nScanning lessons collection …")
    room_inst:    dict[int, dict[int, str]] = defaultdict(dict)
    teacher_inst: dict[int, dict[int, str]] = defaultdict(dict)

    total = 0
    fallback_used = 0

    async for lesson in LessonDoc.find_all():
        total += 1

        # Определяем institute_id/name: прямо или через группу
        iid   = lesson.institute_id
        iname = lesson.institute_name

        if not iid or not iname:
            # Фоллбек: берём из group
            fb = group_inst_map.get(lesson.group_id)
            if fb:
                iid, iname = fb
                fallback_used += 1

        if not iid or not iname:
            continue  # нет данных ни там, ни там

        if lesson.room_id:
            room_inst[lesson.room_id][iid] = iname
        if lesson.teacher_id:
            teacher_inst[lesson.teacher_id][iid] = iname

    print(f"  Scanned      : {total:,} lessons")
    print(f"  Fallback used: {fallback_used:,}  (lessons без institute_id, взяты из group)")
    print(f"  Rooms   with institute data : {len(room_inst)}")
    print(f"  Teachers with institute data: {len(teacher_inst)}")
    return room_inst, teacher_inst


async def migrate_rooms(room_inst: dict[int, dict[int, str]], dry_run: bool):
    print("\n── Rooms ──────────────────────────────────────────────────────────")
    rooms = await Room.find_all().to_list()
    updated = skipped = missing = 0

    for room in rooms:
        mapping = room_inst.get(room.room_id, {})
        if not mapping:
            missing += 1
            continue

        new_ids   = sorted(mapping.keys())
        new_names = [mapping[i] for i in new_ids]

        # Пропускаем если уже актуально
        if sorted(room.institute_ids) == new_ids and sorted(room.institute_names) == sorted(new_names):
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY] room {room.room_id:>6} '{room.name}' "
                  f"{room.institute_ids} → {new_ids}")
        else:
            await Room.find_one(Room.id == room.id).update(
                {"$set": {
                    "institute_ids":   new_ids,
                    "institute_names": new_names,
                }}
            )
        updated += 1

    print(f"  Updated : {updated}")
    print(f"  Skipped : {skipped}  (already correct)")
    print(f"  No data : {missing}  (no lessons found for these rooms)")


async def migrate_teachers(teacher_inst: dict[int, dict[int, str]], dry_run: bool):
    print("\n── Teachers ───────────────────────────────────────────────────────")
    teachers = await Teacher.find_all().to_list()
    updated = skipped = missing = 0

    for teacher in teachers:
        mapping = teacher_inst.get(teacher.teacher_id, {})
        if not mapping:
            missing += 1
            continue

        new_ids   = sorted(mapping.keys())
        new_names = [mapping[i] for i in new_ids]

        if sorted(teacher.institute_ids) == new_ids and sorted(teacher.institute_names) == sorted(new_names):
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY] teacher {teacher.teacher_id:>6} '{teacher.full_name}' "
                  f"{teacher.institute_ids} → {new_ids}")
        else:
            await Teacher.find_one(Teacher.id == teacher.id).update(
                {"$set": {
                    "institute_ids":   new_ids,
                    "institute_names": new_names,
                }}
            )
        updated += 1

    print(f"  Updated : {updated}")
    print(f"  Skipped : {skipped}  (already correct)")
    print(f"  No data : {missing}  (no lessons found for these teachers)")


async def migrate_teacher_source_url(dry_run: bool):
    """
    Одноразовая миграция: проставляет source_url на все записи Teacher
    у которых это поле отсутствует (до добавления поля в модель).
    """
    print("\n── Teacher.source_url backfill ────────────────────────────────────")
    from app.core.config import settings
    from app.db.database import get_motor_db
    db_teachers = get_motor_db()["teachers"]
    without_url = await db_teachers.count_documents(
        {"source_url": {"$exists": False}}
    )
    print(f"  Teachers без source_url: {without_url}")
    if without_url and not dry_run:
        result = await db_teachers.update_many(
            {"source_url": {"$exists": False}},
            {"$set": {"source_url": settings.base_url}},
        )
        print(f"  Updated: {result.modified_count}")
    elif without_url and dry_run:
        print(f"  [DRY] Would set source_url='{settings.base_url}' on {without_url} documents")
    else:
        print("  All teachers already have source_url — skipped")


async def main(dry_run: bool):
    mongo_url = os.environ.get("MONGO_URL") or os.environ.get("MONGODB_URL")
    if not mongo_url:
        print("ERROR: MONGO_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to MongoDB …  {'[DRY RUN]' if dry_run else '[LIVE]'}")
    client = AsyncIOMotorClient(mongo_url)
    db_name = os.environ.get("MONGO_DB", "ncfu")
    await init_beanie(
        database=client[db_name],
        document_models=[Room, Teacher, Group, LessonDoc],
    )

    # Шаг 0: бекфилл source_url на teacher'ов (новое поле)
    await migrate_teacher_source_url(dry_run)

    # Шаг 1: строим маппинги
    group_inst_map = await build_group_institute_map()
    room_inst, teacher_inst = await build_institute_maps(group_inst_map)

    # Шаг 2: обновляем коллекции
    await migrate_rooms(room_inst, dry_run)
    await migrate_teachers(teacher_inst, dry_run)

    client.close()
    print("\nDone." if not dry_run else "\nDry-run complete — no changes written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill institute_ids on rooms/teachers, set source_url on teachers"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
