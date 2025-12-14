from aiogram import Router, F
from aiogram.types import Message
from handlers.db import get_transfers
from config import OPERATORS

router = Router()

@router.message(F.text == "/list")
async def list_done_transfers(message: Message):
    operator_id = message.from_user.id

    if operator_id not in OPERATORS:
        await message.answer("🚫 Ця команда доступна лише для операторів.")
        return

    transfers = get_transfers(operator_id)
    completed = []

    for t in transfers.values():
        if t.get("done"):
            completed.append(
                f"🆔 {t['id']}\n"
                f"📤 {t['sender']['name']} ➡️ 📥 {t['receiver']['name']}"
            )

    if not completed:
        await message.answer("❗ У вас ще немає завершених переміщень.")
        return

    reply_text = "<b>✅ Завершені переміщення:</b>\n\n" + "\n\n".join(completed)
    reply_text += "\n\nЩоб очистити список — введіть /clear"
    await message.answer(reply_text)
