# handlers/confirm.py — підтвердження обраних точок перед початком пересилки

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states import TransferFSM
from keyboards import (
    upload_keyboard,
    confirmation_keyboard,
    action_keyboard,
)
from handlers.storage import active_transfers

router = Router()

@router.message(TransferFSM.confirming_points)
async def confirm_points(message: Message, state: FSMContext):
    text = message.text.strip()

    if text == "✅ Підтвердити точки":
        await state.set_state(TransferFSM.awaiting_media)
        await message.answer(
            "📸 Натисніть - Почати надсилання, або скасувати.",
            reply_markup=upload_keyboard,
        )

    elif text == "❌ Скасувати":
        await state.clear()
        await message.answer(
            "❌ Операцію скасовано. Введіть /start, щоб почати спочатку.",
            reply_markup=action_keyboard,
        )

    else:
        await message.answer(
            "❗ Оберіть один із варіантів: підтвердити, змінити або скасувати.",
            reply_markup=confirmation_keyboard,
        )
