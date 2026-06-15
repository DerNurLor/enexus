#!/usr/bin/env python3
"""
scripts/migrate_null_chat_id.py
================================
One-shot migration that fixes documents in the `conversations` collection
which have chat_id=null (or missing).

Background
----------
The old `ChatMessage` model (collection: chat_messages) did not have a
`chat_id` field — only `tg_id` (the user's Telegram ID).  When the schema
was migrated to the new `Message` model (collection: conversations), some
documents were copied over without setting `chat_id`, leaving it null.

This causes two runtime problems:
  1. The aggregation in GET /dashboard/api/chats groups all null-chat_id docs
     into a single {_id: null} bucket, which the UI renders as "chat:null".
  2. Clicking that entry calls /chats/null, which FastAPI rejects with a
     type error because `chat_id` is typed as `int` in the path.

Strategy
--------
For private-chat messages (role: user|bot), `tg_id` is the only identifier
we have.  We treat `tg_id` as the `chat_id` for private chats — this is
correct for Telegram, where the chat ID of a private conversation IS the
user's Telegram ID.

Documents that have neither `chat_id` nor `tg_id` (corrupted records) are
deleted, with a count reported to stdout.

Run
---
    python scripts/migrate_null_chat_id.py [--dry-run] [--delete-orphans]

Options
    --dry-run         Print what would happen without writing anything.
    --delete-orphans  Delete documents that have chat_id=null AND tg_id=null
                      instead of skipping them.  Default: skip and report.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv



load_dotenv()

MONGO_URI     = os.getenv("MONGO_URI",     "mongodb://mongo:27017")
AUTH_MONGO_DB = os.getenv("AUTH_MONGO_DB", "ncfu_auth")
COLLECTION    = "conversations"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")

def log(msg: str) -> None:
    print(f"[{_now()}] {msg}")



async def run(dry_run: bool, delete_orphans: bool) -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    col    = client[AUTH_MONGO_DB][COLLECTION]

    total_null = await col.count_documents({"chat_id": None})
    log(f"Documents with chat_id=null: {total_null}")
    if total_null == 0:
        log("Nothing to do. Exiting.")
        client.close()
        return

    fixable  = await col.count_documents({"chat_id": None, "tg_id": {"$ne": None}})
    orphaned = await col.count_documents({"chat_id": None, "tg_id": None})
    log(f"  Fixable  (have tg_id): {fixable}")
    log(f"  Orphaned (no  tg_id): {orphaned}")

    if dry_run:
        log("DRY RUN — no writes will be performed.")

    # For Telegram private chats, chat.id == user.id, so this is semantically correct.
    log("Fixing documents: chat_id ← tg_id, chat_type ← 'private' ...")

    fixed = 0
    if not dry_run:
        # Use updateMany with an aggregation pipeline so we can reference another field ($tg_id).
        result = await col.update_many(
            {"chat_id": None, "tg_id": {"$ne": None}},
            [
                {"$set": {
                    "chat_id":   "$tg_id",
                    "chat_type": {"$ifNull": ["$chat_type", "private"]},
                    # chat_key = "{chat_id}:0"  — thread_id always 0 for private
                    "chat_key":  {"$concat": [
                        {"$toString": "$tg_id"}, ":0"
                    ]},
                }},
            ],
        )
        fixed = result.modified_count
        log(f"  Updated {fixed} documents.")
    else:
        log(f"  Would update {fixable} documents.")

    if orphaned > 0:
        if delete_orphans:
            log(f"Deleting {orphaned} orphaned documents (no chat_id, no tg_id) ...")
            if not dry_run:
                result = await col.delete_many({"chat_id": None, "tg_id": None})
                log(f"  Deleted {result.deleted_count} documents.")
            else:
                log(f"  Would delete {orphaned} documents.")
        else:
            log(
                f"WARNING: {orphaned} orphaned documents remain (chat_id=null, tg_id=null). "
                "Re-run with --delete-orphans to remove them."
            )

    # -- Verify ---------------------------------------------------------------
    remaining = await col.count_documents({"chat_id": None})
    log(f"Remaining null chat_id docs: {remaining}")
    if remaining == 0:
        log("Migration complete. Collection is clean.")
    else:
        log("Migration partial — some documents still have chat_id=null.")

    client.close()



def main() -> None:
    parser = argparse.ArgumentParser(description="Fix null chat_id in conversations collection.")
    parser.add_argument("--dry-run",        action="store_true", help="No writes, just report.")
    parser.add_argument("--delete-orphans", action="store_true", help="Delete docs with no tg_id.")
    args = parser.parse_args()

    asyncio.run(run(dry_run=args.dry_run, delete_orphans=args.delete_orphans))


if __name__ == "__main__":
    main()
