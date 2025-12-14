# handlers/base.py — перший етап: вибір підгруп і точок

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states import TransferFSM
from config import OPERATORS, CITY_GROUPS
from keyboards import (
    group_keyboard,
    point_keyboard,
    cancel_keyboard,
    confirmation_keyboard,
)
from aiogram.types import ReplyKeyboardRemove

router = Router()

# 📲 /start
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id
    if user_id in OPERATORS:
        await message.answer(
            "Оператор👋 - Виберіть підгрупу відправника:",
            reply_markup=group_keyboard(),
        )
        await state.set_state(TransferFSM.choosing_sender_group)
        return

    for group, points in CITY_GROUPS.items():
        for point in points:
            if point["id"] == user_id:
                await message.answer(
                    f"✅ Ви увійшли як точка: <b>{point['name']}</b>",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

    await message.answer("🚫 У вас немає доступу.", reply_markup=ReplyKeyboardRemove())

# ❌ Скасування
@router.message(F.text == "❌ Скасувати")
async def cancel_all(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔁 Скасовано. Введіть /start, щоб почати знову.",
        reply_markup=cancel_keyboard,
    )

# 📦 Вибір підгрупи відправника
@router.message(TransferFSM.choosing_sender_group)
async def sender_group(message: Message, state: FSMContext):
    group = message.text
    if group not in CITY_GROUPS:
        await message.answer("❗ Невірна підгрупа")
        return
    await state.update_data(sender_group=group)
    await message.answer(
        "📍 Оберіть точку відправника:",
        reply_markup=point_keyboard(group),
    )
    await state.set_state(TransferFSM.choosing_sender_point)

# 📍 Вибір точки відправника
@router.message(TransferFSM.choosing_sender_point)
async def sender_point(message: Message, state: FSMContext):
    data = await state.get_data()
    group = data.get("sender_group")
    name = message.text
    point = next((p for p in CITY_GROUPS[group] if p["name"] == name), None)
    if not point:
        await message.answer("❗ Невірна точка")
        return
    await state.update_data(sender_point=point)
    await message.answer(
        "📦 Оберіть підгрупу отримувача:",
        reply_markup=group_keyboard(),
    )
    await state.set_state(TransferFSM.choosing_receiver_group)

# 📍 Вибір підгрупи отримувача
@router.message(TransferFSM.choosing_receiver_group)
async def receiver_group(message: Message, state: FSMContext):
    group = message.text
    if group not in CITY_GROUPS:
        await message.answer("❗ Невірна підгрупа")
        return
    await state.update_data(receiver_group=group)
    await message.answer(
        "📥 Оберіть точку отримувача:",
        reply_markup=point_keyboard(group),
    )
    await state.set_state(TransferFSM.choosing_receiver_point)

# 📥 Вибір точки отримувача
@router.message(TransferFSM.choosing_receiver_point)
async def receiver_point(message: Message, state: FSMContext):
    data = await state.get_data()
    group = data.get("receiver_group")
    name = message.text
    point = next((p for p in CITY_GROUPS[group] if p["name"] == name), None)
    if not point:
        await message.answer("❗ Невірна точка")
        return
    await state.update_data(receiver_point=point)

    sender = data["sender_point"]
    await message.answer(
        f"✅ Ви обрали точки:\n"
        f"📤 Відправник: {sender['name']} ({sender['id']})\n"
        f"📥 Отримувач: {point['name']} ({point['id']})\n\n"
        f"Підтвердіть або змініть вибір:",
        reply_markup=confirmation_keyboard,
    )
    await state.set_state(TransferFSM.confirming_points)
