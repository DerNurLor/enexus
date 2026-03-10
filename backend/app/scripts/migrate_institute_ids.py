#!/usr/bin/env python3
"""
migrate_institute_ids.py
────────────────────────
Backfills `institute_ids` and `institute_names` on:
  - rooms      (Room collection) — derived from LessonDoc
  - teachers   (Teacher collection) — derived from LessonDoc (double-check existing data)

Usage:
    cd backend
    python scripts/migrate_institute_ids.py

    # Dry-run (prints what would change, writes nothing):
    python scripts/migrate_institute_ids.py --dry-run

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
from app.models.lesson  import LessonDoc


async def build_institute_maps():
    """
    Scan LessonDoc once and build two maps:
        room_id    → {institute_id: institute_name, ...}
        teacher_id → {institute_id: institute_name, ...}
    """
    print("Scanning lessons collection …")
    room_inst:    dict[int, dict[int, str]] = defaultdict(dict)
    teacher_inst: dict[int, dict[int, str]] = defaultdict(dict)

    total = 0
    async for lesson in LessonDoc.find_all():
        total += 1
        if lesson.institute_id and lesson.institute_name:
            if lesson.room_id:
                room_inst[lesson.room_id][lesson.institute_id] = lesson.institute_name
            if lesson.teacher_id:
                teacher_inst[lesson.teacher_id][lesson.institute_id] = lesson.institute_name

    print(f"  Scanned {total:,} lessons")
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

        # Skip if already correct
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
        document_models=[Room, Teacher, LessonDoc],
    )

    room_inst, teacher_inst = await build_institute_maps()
    await migrate_rooms(room_inst, dry_run)
    await migrate_teachers(teacher_inst, dry_run)

    client.close()
    print("\nDone." if not dry_run else "\nDry-run complete — no changes written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill institute_ids on rooms and teachers")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
