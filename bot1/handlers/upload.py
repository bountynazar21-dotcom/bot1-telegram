# handlers/upload.py — обробка завантаження фото накладної

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states import TransferFSM
from keyboards import upload_keyboard, combined_finish_keyboard, point_confirm_keyboard
from handlers.storage import status_tracker
from handlers.storage import generate_transfer_id
from handlers.db import save_transfer, get_transfers, delete_old_transfers


router = Router()

photo_buffer = {}            # Зберігає file_id фото
photo_caption_buffer = {}    # Зберігає кастомні підписи до фото


# 📸 Почати надсилання
@router.message(F.text == "📸 Почати надсилання")
async def start_uploading(message: Message, state: FSMContext):
    await state.set_state(TransferFSM.uploading_photos)
    photo_buffer[message.from_user.id] = []
    photo_caption_buffer[message.from_user.id] = []
    await message.answer(
        "📤 Надсилайте фото одне за одним. Після кожного фото можете відправити текст-підпис. "
        "Коли завершите — натисніть '📦 Завершити надсилання'.",
        reply_markup=combined_finish_keyboard
    )


# 🖼️ Обробка фото
@router.message(TransferFSM.uploading_photos, F.photo)
async def collect_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id

    # Зберігаємо фото
    photo_buffer.setdefault(user_id, []).append(photo_id)
    # Створюємо пустий підпис для цього фото
    photo_caption_buffer.setdefault(user_id, []).append("")
    
    await message.answer("✅ Фото збережено. Надішліть підпис для фото або надішліть нове фото.")


# ✏️ Обробка підписів
@router.message(TransferFSM.uploading_photos, F.text & ~F.text.in_(["📦 Завершити надсилання"]))
async def add_caption(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in photo_buffer and photo_buffer[user_id]:
        # Зберігаємо текст як підпис до останнього фото
        last_index = len(photo_buffer[user_id]) - 1
        photo_caption_buffer[user_id][last_index] = message.text.strip()
        await message.answer("✏️ Підпис збережено. Надішліть ще фото або завершіть надсилання.")
    else:
        await message.answer("⚠️ Спочатку надішліть фото.")


# 📦 Завершення надсилання
@router.message(TransferFSM.uploading_photos, F.text == "📦 Завершити надсилання")
async def finish_upload(message: Message, state: FSMContext):
    data = await state.get_data()
    sender = data.get("sender_point")
    receiver = data.get("receiver_point")
    user_id = message.from_user.id

    photos = photo_buffer.get(user_id, [])
    captions = photo_caption_buffer.get(user_id, [])

    if not sender or not receiver:
        await message.answer("⚠️ Помилка: не обрано відправника або отримувача. Спочатку оберіть точки.")
        return

    if not photos:
        await message.answer("⚠️ Ви ще не надіслали жодного фото.")
        return

    # 🆔 Генерація ID переміщення
    transfer_id = generate_transfer_id()
    operator_id = user_id

    for pid, custom_caption in zip(photos, captions):
        # Формуємо дефолтні тексти
        default_caption_sender = "📤 Відайте товар згідно з накладною."
        default_caption_receiver = "📥 Очікуйте товар згідно з накладною."

        # Якщо кастомний підпис існує — додаємо його
        custom_part = f"\n\n{custom_caption}" if custom_caption else ""

        # Додаємо ID переміщення
        transfer_id_part = f"\n\n🆔 Переміщення: #{transfer_id}"

        # Повний caption для відправника
        combined_caption_sender = default_caption_sender + custom_part + transfer_id_part

        # Повний caption для отримувача
        combined_caption_receiver = default_caption_receiver + custom_part + transfer_id_part

        await message.bot.send_photo(
            sender["id"],
            pid,
            caption=combined_caption_sender,
            reply_markup=point_confirm_keyboard
        )
        await message.bot.send_photo(
            receiver["id"],
            pid,
            caption=combined_caption_receiver,
            reply_markup=point_confirm_keyboard
        )

    # ✅ Збереження переміщення у словник
    status_tracker.setdefault(operator_id, {})[transfer_id] = {
        "id": transfer_id,
        "sender": sender,
        "receiver": receiver,
        "photos": photos,
        "captions": captions,   # ← ДОДАНО captions для дублювання
        "sender_ok": False,
        "receiver_ok": False,
        "done": False,
        "reason": None
    }

    # Очищаємо буфери
    photo_buffer[operator_id] = []
    photo_caption_buffer[operator_id] = []

    await state.clear()

    await message.answer(
        f"✅ Фото надіслані обом точкам.\n"
        f"🆔 ID переміщення: #{transfer_id}",
        reply_markup=combined_finish_keyboard
    )


# ✅ Функція дублювання накладної оператору
async def send_transfer_copy(bot, user_id, transfer_id):
    transfers = status_tracker.get(user_id, {})
    transfer = transfers.get(transfer_id)

    if not transfer:
        await bot.send_message(
            user_id,
            f"⚠️ Переміщення з ID #{transfer_id} не знайдено."
        )
        return

    photos = transfer.get("photos", [])
    captions = transfer.get("captions", [])
    sender = transfer.get("sender")
    receiver = transfer.get("receiver")

    for i, pid in enumerate(photos):
        custom_caption = captions[i] if i < len(captions) else ""
        default_caption = "🔄 Копія накладної для перегляду."
        transfer_caption = f"🆔 Переміщення: #{transfer_id}"

        full_caption = default_caption
        if custom_caption:
            full_caption += f"\n\n{custom_caption}"
        full_caption += f"\n\n{transfer_caption}"

        await bot.send_photo(
            user_id,
            pid,
            caption=full_caption
        )

    await bot.send_message(
        user_id,
        f"✅ Ви переглянули переміщення #{transfer_id}"
    )
