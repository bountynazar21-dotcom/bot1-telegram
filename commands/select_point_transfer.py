from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from handlers.storage import active_transfers
from handlers.db import get_transfers
from config import OPERATORS

router = Router()

class PointSelectFSM(StatesGroup):
    waiting_for_id = State()

# ── Reply-клава ТІЛЬКИ для торгових точок: 2 кнопки поруч ─────────────────────
def tt_actions_keyboard() -> ReplyKeyboardMarkup:
    rows = [[
        KeyboardButton(text="✅ Віддав товар"),
        KeyboardButton(text="📬 Отримав товар"),
    ]]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        one_time_keyboard=False,   # не зникає після натискання
        input_field_placeholder="Обери дію…"
    )

@router.message(F.text == "/mytransfers")
async def list_point_transfers(message: Message, state: FSMContext):
    user_id = message.from_user.id

    sent_transfers = []
    received_transfers = []

    for operator_id in OPERATORS:
        transfers = get_transfers(operator_id)
        for t in transfers.values():
            if t.get("done"):
                continue

            sender_id = t["sender"].get("id")
            receiver_id = t["receiver"].get("id")

            if sender_id == user_id:
                status = (
                    "✅ Ви вже видали товар, чекаємо отримувача."
                    if t.get("sender_ok") and not t.get("receiver_ok")
                    else "❌ Ви ще не підтвердили видачу товару."
                )
                sent_transfers.append(
                    (t["id"], t["sender"]["name"], t["receiver"]["name"], status)
                )
            elif receiver_id == user_id:
                status = (
                    "✅ Ви вже підтвердили отримання, чекаємо відправника."
                    if t.get("receiver_ok") and not t.get("sender_ok")
                    else "❌ Ви ще не підтвердили отримання товару."
                )
                received_transfers.append(
                    (t["id"], t["sender"]["name"], t["receiver"]["name"], status)
                )

    if not sent_transfers and not received_transfers:
        await message.answer("🔕 У вас немає активних переміщень.")
        return

    text = "<b>📦 Ваші переміщення:</b>\n\n"

    if sent_transfers:
        text += "🔸 <b>Ви як відправник:</b>\n"
        for t_id, sender, receiver, status in sent_transfers:
            text += (
                f"🆔 {t_id}\n"
                f"📤 {sender} ➡️ 📥 {receiver}\n"
                f"Статус: {status}\n\n"
            )

    if received_transfers:
        text += "🔹 <b>Ви як отримувач:</b>\n"
        for t_id, sender, receiver, status in received_transfers:
            text += (
                f"🆔 {t_id}\n"
                f"📤 {sender} ➡️ 📥 {receiver}\n"
                f"Статус: {status}\n\n"
            )

    text += "🔽 Введіть ID переміщення, з яким хочете працювати:"
    await message.answer(text)
    await state.set_state(PointSelectFSM.waiting_for_id)

@router.message(PointSelectFSM.waiting_for_id, F.text)
async def receive_transfer_choice(message: Message, state: FSMContext):
    user_id = message.from_user.id
    input_id = message.text.strip()

    for operator_id in OPERATORS:
        transfers = get_transfers(operator_id)
        if input_id in transfers:
            transfer = transfers[input_id]
            if transfer.get("done"):
                await message.answer("⚠️ Це переміщення вже завершено.")
                return

            if user_id in (
                transfer["sender"].get("id"),
                transfer["receiver"].get("id"),
            ):
                # ✅ робимо активним
                active_transfers[user_id] = input_id

                # ✅ показуємо дві кнопки лише для ТТ
                reply_markup = None
                if user_id not in OPERATORS:
                    reply_markup = tt_actions_keyboard()

                await message.answer(
                    f"✅ Обрано переміщення <b>{input_id}</b> як активне.",
                    reply_markup=reply_markup
                )
                await state.clear()
                return

    await message.answer("❗ Таке переміщення не знайдено серед ваших.")
