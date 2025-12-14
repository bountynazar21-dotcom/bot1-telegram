from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OPERATORS
from handlers.db import get_transfers, save_transfer
from handlers.storage import active_transfers

router = Router()

class FinishFSM(StatesGroup):
    waiting_for_id = State()

@router.message(F.text == "/finish")
async def start_finish(message: Message, state: FSMContext):
    operator_id = message.from_user.id

    if operator_id not in OPERATORS:
        await message.answer("🚫 Ця команда доступна лише для операторів.")
        return

    transfers = get_transfers(operator_id)
    active = [t for t in transfers.values() if not t.get("done")]

    if not active:
        await message.answer("🔕 У вас немає активних переміщень.")
        return

    text = "<b>🔀 Активні переміщення:</b>\n\n"
    for t in active:
        text += f"🆔 {t['id']}\n📤 {t['sender']['name']} ➡️ 📥 {t['receiver']['name']}\n\n"

    text += "🔽 Введіть ID переміщення, яке хочете завершити:"
    await message.answer(text)
    await state.set_state(FinishFSM.waiting_for_id)

@router.message(FinishFSM.waiting_for_id, F.text)
async def receive_transfer_id(message: Message, state: FSMContext):
    operator_id = message.from_user.id
    input_id = message.text.strip()
    transfers = get_transfers(operator_id)

    if input_id not in transfers:
        await message.answer("❗ Таке ID не знайдено серед ваших переміщень.")
        return

    transfer = transfers[input_id]

    if transfer.get("done"):
        await message.answer("⚠️ Це переміщення вже завершено.")
        await state.clear()
        return

    # ✅ Міняємо статус
    transfer["done"] = True

    # ✅ Зберігаємо зміни назад у БД
    save_transfer(
        transfer_id=input_id,
        operator_id=operator_id,
        sender=transfer["sender"],
        receiver=transfer["receiver"],
        photos=transfer["photos"],
        captions=transfer["captions"],
        sender_ok=transfer["sender_ok"],
        receiver_ok=transfer["receiver_ok"],
        done=True,
        reason=transfer["reason"]
    )

    # Видаляємо з active_transfers, якщо був вибраний
    if operator_id in active_transfers and active_transfers[operator_id] == input_id:
        active_transfers.pop(operator_id, None)

    # ✅ Сповіщаємо точки!
    sender_id = transfer["sender"]["id"]
    receiver_id = transfer["receiver"]["id"]

    # Повідомлення відправнику
    await message.bot.send_message(
        sender_id,
        f"⚠️ Оператор <b>завершив переміщення #{input_id}</b> вручну.\n"
        f"Переміщення вважається закритим."
    )

    # Повідомлення отримувачу
    await message.bot.send_message(
        receiver_id,
        f"⚠️ Оператор <b>завершив переміщення #{input_id}</b> вручну.\n"
        f"Переміщення вважається закритим."
    )

    # ✅ Повідомлення оператору
    await message.answer(
        f"✅ Переміщення <b>{input_id}</b> позначено як завершене і точки повідомлено."
    )

    await state.clear()

