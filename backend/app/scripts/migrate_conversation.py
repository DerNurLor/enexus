import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


async def migrate():
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.auth_mongo_db]


    old_col = db['conversations']
    new_col = db['messages']


    # Создать уникальный индекс чтобы избежать дублей при повторном запуске
    await new_col.create_index(
        [('chat_id', 1), ('message_id', 1)],
        unique=True, background=True
    )


    cursor = old_col.find({}, batch_size=500)
    migrated, skipped = 0, 0


    async for doc in cursor:
        tg_id = doc.get('tg_id', 0)
        # Старые документы — личные чаты (chat_id == tg_id для private)
        new_doc = {
            **doc,
            'chat_id':   tg_id,        # private: chat_id == user tg_id
            'chat_key':  f'{tg_id}:0',
            'chat_type': 'private',
            'thread_id': None,
            'message_type': _infer_type(doc),
        }
        try:
            await new_col.insert_one(new_doc)
            migrated += 1
        except Exception:  # duplicate key — уже мигрировано
            skipped += 1


    print(f'Migrated: {migrated}, Skipped (duplicates): {skipped}')


def _infer_type(doc: dict) -> str:
    media = doc.get('media')
    if not media:
        return 'text'
    return media.get('kind', 'unknown')


if __name__ == '__main__':
    asyncio.run(migrate())

