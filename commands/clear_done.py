from aiogram import Router, F
from aiogram.types import Message
from handlers.db import get_transfers, delete_transfer_by_id
from config import OPERATORS

router = Router()

@router.message(F.text == "/clear")
async def clear_done_transfers(message: Message):
    operator_id = message.from_user.id

    if operator_id not in OPERATORS:
        await message.answer("🚫 Ця команда доступна лише для операторів.")
        return

    transfers = get_transfers(operator_id)

    if not transfers:
        await message.answer("⚠️ У вас немає переміщень.")
        return

    # Збираємо id завершених переміщень
    done_ids = [
        tid for tid, t in transfers.items()
        if t.get("done")
    ]

    for tid in done_ids:
        delete_transfer_by_id(tid)

    await message.answer(f"🧹 Видалено {len(done_ids)} завершених переміщень.")
