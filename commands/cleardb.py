# commands/cleardb.py

from aiogram import Router, F
from aiogram.types import Message
from config import OPERATORS
from handlers.db import clear_transfers_but_keep_counter

router = Router()

@router.message(F.text == "/cleardb")
async def clear_db_command(message: Message):
    user_id = message.from_user.id

    if user_id not in OPERATORS:
        await message.answer("🚫 Ця команда доступна лише для операторів.")
        return

    clear_transfers_but_keep_counter()

    await message.answer(
        "🧹 Базу даних очищено. Лічильник ID залишено без змін."
    )
