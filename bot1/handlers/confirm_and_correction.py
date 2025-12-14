from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery


from config import OPERATORS
from keyboards import point_confirm_keyboard, combined_finish_keyboard
from handlers.storage import status_tracker, pending_corrections
from states import TransferFSM
from handlers.db import save_transfer, get_transfers, delete_old_transfers


router = Router()

# ✅ Відав товар
@router.message(F.text == "✅ Відав товар")
async def handle_sender_confirm(message: Message):
    user_id = message.from_user.id
    for operator_id, transfers in status_tracker.items():
        for track in transfers.values():
            if track.get("sender", {}).get("id") == user_id and not track.get("sender_ok"):
                track["sender_ok"] = True

                # Повідомлення відправнику
                await message.answer(
                    "✅ Дякуємо! Ви підтвердили, що видали товар.",
                    reply_markup=point_confirm_keyboard
                )

                # Повідомлення отримувачу
                await message.bot.send_message(
                    track["receiver"]["id"],
                    f"📤 Відправник {track['sender']['name']} підтвердив видачу товару.\n"
                    f"Тепер ваша черга — натисніть «📬 Отримав товар», якщо дійсно отримали.",
                    reply_markup=point_confirm_keyboard
                )

                # 🔔 Повідомлення оператору
                await message.bot.send_message(
                    operator_id,
                    f"📤 Відправник <b>{track['sender']['name']}</b> підтвердив видачу товару "
                    f"у переміщенні <b>{track['id']}</b>."
                )

                await check_full_confirmation(track, operator_id, message.bot)
                return

    await message.answer("⚠️ Ви не є відправником або вже підтвердили.")

# 📬 Отримав товар
@router.message(F.text == "📬 Отримав товар")
async def handle_receiver_confirm(message: Message):
    user_id = message.from_user.id
    for operator_id, transfers in status_tracker.items():
        for track in transfers.values():  # ✅
            if track.get("receiver", {}).get("id") == user_id and not track.get("receiver_ok"):
                track["receiver_ok"] = True
                await message.answer("📬 Дякуємо! Ви підтвердили отримання товару.", reply_markup=point_confirm_keyboard)
                await message.bot.send_message(
                    track["sender"]["id"],
                    f"📅 Отримувач {track['receiver']['name']} підтвердив отримання.",
                    reply_markup=point_confirm_keyboard
                )
                await check_full_confirmation(track, operator_id, message.bot)
                return
    await message.answer("⚠️ Ви не є отримувачем або вже підтвердили.")

async def check_full_confirmation(track, operator_id, bot):
    if track.get("sender_ok") and track.get("receiver_ok") and not track.get("done"):
        track["done"] = True
        await bot.send_message(
            operator_id,
            f"✅ Успішно, переміщення підтвердили дві точки\n"
            f"🆔 ID: {track['id']}\n"
            f"📤 Відправник: {track['sender']['name']} ({track['sender']['id']})\n"
            f"📬 Отримувач: {track['receiver']['name']} ({track['receiver']['id']})",
            reply_markup=combined_finish_keyboard
        )
# 📌 1. Обробка callback від інлайн кнопки
@router.callback_query(F.data.startswith("resend:"))
async def handle_resend(callback: CallbackQuery, state: FSMContext):
    transfer_id = callback.data.split(":")[1]
    operator_id = callback.from_user.id
    await state.set_state(TransferFSM.uploading_corrected)
    await state.update_data(transfer_id=transfer_id, operator_id=operator_id)
    await callback.message.answer("📸 Завантажте оновлену накладну (фото):")
    await callback.answer()

# 📌 2. Приймаємо фото та надсилаємо обом точкам
@router.message(TransferFSM.uploading_corrected, F.photo)
async def handle_corrected_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    operator_id = data["operator_id"]
    transfer_id = data["transfer_id"]

    file_id = message.photo[-1].file_id

    transfers = status_tracker.get(operator_id, {})
    transfer = transfers.get(transfer_id)

    if not transfer:
        await message.answer("❌ Переміщення не знайдено.")
        await state.clear()
        return

    # Зберігаємо нове фото
    transfer["photo"] = file_id

    # Надсилаємо оновлену накладну точкам
    await message.bot.send_photo(
        transfer["sender"]["id"],
        file_id,
        caption=f"🔁 Оновлена накладна по переміщенню #{transfer_id}"
    )
    await message.bot.send_photo(
        transfer["receiver"]["id"],
        file_id,
        caption=f"🔁 Оновлена накладна по переміщенню #{transfer_id}"
    )

    await message.answer("✅ Оновлену накладну надіслано обом точкам.")
    await state.clear()
       