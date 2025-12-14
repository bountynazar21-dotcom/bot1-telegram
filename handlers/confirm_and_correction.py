from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import OPERATORS
from keyboards import point_confirm_keyboard, combined_finish_keyboard
from handlers.storage import active_transfers
from handlers.db import get_transfers, save_transfer
from states import TransferFSM

router = Router()

# ✅ Відав товар
@router.message(F.text == "✅ Віддав товар")
async def handle_sender_confirm(message: Message):
    user_id = message.from_user.id
    transfer_id = active_transfers.get(user_id)

    if not transfer_id:
        await message.answer("⚠️ У вас не вибрано активне переміщення. Використайте /mytransfers.")
        return

    for operator_id in OPERATORS:
        transfers = get_transfers(operator_id)
        track = transfers.get(transfer_id)

        if not track:
            continue

        if track.get("done"):
            await message.answer("⚠️ Це переміщення вже завершено.")
            return

        if user_id != track["sender"]["id"]:
            await message.answer("⚠️ Ви не є відправником у цьому переміщенні.")
            return

        if track["sender_ok"]:
            await message.answer("⚠️ Ви вже підтвердили видачу товару.")
            return

        # ✅ Позначаємо видачу
        track["sender_ok"] = True
        save_transfer(
            transfer_id=track["id"],
            operator_id=operator_id,
            sender=track["sender"],
            receiver=track["receiver"],
            photos=track["photos"],
            captions=track["captions"],
            sender_ok=True,
            receiver_ok=track["receiver_ok"],
            done=track["done"],
            reason=track["reason"],
        )

        await message.answer(
            "✅ Дякуємо! Ви підтвердили, що видали товар.",
            reply_markup=point_confirm_keyboard,
        )

        await message.bot.send_message(
            track["receiver"]["id"],
            f"📤 Відправник {track['sender']['name']} підтвердив видачу товару у переміщенні <b>{track['id']}</b>.\n"
            f"Тепер ваша черга — натисніть «📬 Отримав товар», якщо дійсно отримали.",
            reply_markup=point_confirm_keyboard,
        )

        await message.bot.send_message(
            operator_id,
            f"📤 Відправник <b>{track['sender']['name']}</b> підтвердив видачу товару "
            f"у переміщенні <b>{track['id']}</b>."
        )

        await check_full_confirmation(track, operator_id, message.bot)
        return

    await message.answer("⚠️ Переміщення не знайдено.")


# 📬 Отримав товар
@router.message(F.text == "📬 Отримав товар")
async def handle_receiver_confirm(message: Message):
    user_id = message.from_user.id
    transfer_id = active_transfers.get(user_id)

    if not transfer_id:
        await message.answer("⚠️ У вас не вибрано активне переміщення. Використайте /mytransfers.")
        return

    for operator_id in OPERATORS:
        transfers = get_transfers(operator_id)
        track = transfers.get(transfer_id)

        if not track:
            continue

        if track.get("done"):
            await message.answer("⚠️ Це переміщення вже завершено.")
            return

        if user_id != track["receiver"]["id"]:
            await message.answer("⚠️ Ви не є отримувачем у цьому переміщенні.")
            return

        if track["receiver_ok"]:
            await message.answer("⚠️ Ви вже підтвердили отримання товару.")
            return

        # ✅ Позначаємо отримання
        track["receiver_ok"] = True
        save_transfer(
            transfer_id=track["id"],
            operator_id=operator_id,
            sender=track["sender"],
            receiver=track["receiver"],
            photos=track["photos"],
            captions=track["captions"],
            sender_ok=track["sender_ok"],
            receiver_ok=True,
            done=track["done"],
            reason=track["reason"],
        )

        await message.answer(
            "📬 Дякуємо! Ви підтвердили отримання товару.",
            reply_markup=point_confirm_keyboard,
        )

        await message.bot.send_message(
            track["sender"]["id"],
            f"📅 Отримувач {track['receiver']['name']} підтвердив отримання "
            f"у переміщенні <b>{track['id']}</b>.",
            reply_markup=point_confirm_keyboard,
        )

        await message.bot.send_message(
            operator_id,
            f"📬 Отримувач <b>{track['receiver']['name']}</b> підтвердив отримання "
            f"у переміщенні <b>{track['id']}</b>."
        )

        await check_full_confirmation(track, operator_id, message.bot)
        return

    await message.answer("⚠️ Переміщення не знайдено.")


async def check_full_confirmation(track, operator_id, bot):
    if track.get("sender_ok") and track.get("receiver_ok") and not track.get("done"):
        track["done"] = True

        save_transfer(
            transfer_id=track["id"],
            operator_id=operator_id,
            sender=track["sender"],
            receiver=track["receiver"],
            photos=track["photos"],
            captions=track["captions"],
            sender_ok=track["sender_ok"],
            receiver_ok=track["receiver_ok"],
            done=True,
            reason=track["reason"],
        )

        await bot.send_message(
            operator_id,
            f"✅ Успішно, переміщення підтвердили дві точки\n"
            f"🆔 ID: {track['id']}\n"
            f"📤 Відправник: {track['sender']['name']} ({track['sender']['id']})\n"
            f"📬 Отримувач: {track['receiver']['name']} ({track['receiver']['id']})",
            reply_markup=combined_finish_keyboard,
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

    transfers = get_transfers(operator_id)
    transfer = transfers.get(transfer_id)

    if not transfer:
        await message.answer("❌ Переміщення не знайдено.")
        await state.clear()
        return

    # Додаємо нове фото в список photos
    transfer["photos"].append(file_id)
    transfer["captions"].append("🔁 Оновлена накладна")

    save_transfer(
        transfer_id=transfer["id"],
        operator_id=operator_id,
        sender=transfer["sender"],
        receiver=transfer["receiver"],
        photos=transfer["photos"],
        captions=transfer["captions"],
        sender_ok=transfer["sender_ok"],
        receiver_ok=transfer["receiver_ok"],
        done=transfer["done"],
        reason=transfer["reason"],
    )

    # Надсилаємо оновлену накладну точкам
    await message.bot.send_photo(
        transfer["sender"]["id"],
        file_id,
        caption=f"🔁 Оновлена накладна по переміщенню #{transfer_id}",
    )
    await message.bot.send_photo(
        transfer["receiver"]["id"],
        file_id,
        caption=f"🔁 Оновлена накладна по переміщенню #{transfer_id}",
    )

    await message.answer("✅ Оновлену накладну надіслано обом точкам.")
    await state.clear()
