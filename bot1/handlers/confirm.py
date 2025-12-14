# handlers/confirm.py — підтвердження обраних точок перед початком пересилки

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states import TransferFSM
from keyboards import upload_keyboard, confirmation_keyboard, action_keyboard, combined_finish_keyboard# ← оце тут
from handlers.storage import active_transfers, status_tracker
from handlers.db import save_transfer, get_transfers, delete_old_transfers


router = Router()

@router.message(TransferFSM.confirming_points)
async def confirm_points(message: Message, state: FSMContext):
    text = message.text.strip()

    if text == "✅ Підтвердити точки":
        await state.set_state(TransferFSM.awaiting_media)
        await message.answer("📸 Натисніть - Почати надсилання , або скасувати ", reply_markup=upload_keyboard)

    elif text == "❌ Скасувати":
        await state.clear()
        await message.answer("❌ Операцію скасовано. Введіть /start щоб почати спочатку.", reply_markup=action_keyboard)

    else:
        await message.answer("❗ Оберіть один із варіантів: підтвердити, змінити або скасувати.", reply_markup=confirmation_keyboard)

@router.message(F.text == "✅ Закінчити переміщення")
async def finish_transfer(message: Message):
    operator_id = message.from_user.id
    current_id = active_transfers.get(operator_id)

    if not current_id:
        await message.answer("❗ У вас не обрано жодного активного переміщення.")
        return

    transfers = status_tracker.get(operator_id, {})
    transfer = transfers.get(current_id)

    if not transfer:
        await message.answer("⚠️ Переміщення не знайдено.")
        return

    if transfer.get("done"):
        await message.answer(f"🔒 Переміщення <b>{current_id}</b> вже завершене.")
        return

    transfer["done"] = True
    active_transfers.pop(operator_id, None)

    await message.answer(f"✅ Переміщення <b>{current_id}</b> позначено як завершене.")