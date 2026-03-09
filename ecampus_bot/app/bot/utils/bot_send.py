from aiogram import Bot
from aiogram.types import Message
from app.bot.message_store import store_message


async def send_and_store(bot: Bot, chat_id: int, text: str, **kwargs) -> Message:
    """
    Отправляет сообщение и сохраняет его в conversations
    """

    msg = await bot.send_message(chat_id, text, **kwargs)

    await store_message(msg, role="bot")

    return msg
