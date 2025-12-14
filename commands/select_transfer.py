from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from handlers.storage import active_transfers
from handlers.db import get_transfers
from handlers.upload import send_transfer_copy
from config import OPERATORS

import re

router = Router()

class SelectFSM(StatesGroup):
    waiting_for_id = State()

def _id_sort_key(tid: str):
    """
    Natural sort: спершу за числовою частиною ID (якщо є), потім лексикографічно.
    Це дає послідовність від "старіших" до "новіших", якщо ID інкрементні.
    """
    m = re.search(r'\d+', tid)
    return (int(m.group()) if m else float('inf'), tid)

@router.message(F.text == "/select")
async def start_select(message: Message, state: FSMContext):
    operator_id = message.from_user.id

    if operator_id not in OPERATORS:
        await message.answer("🚫 Ця команда доступна лише для операторів.")
        return

    transfers = get_transfers(operator_id)  # dict: {id: transfer}
    if not transfers:
        await message.answer("🔕 У вас немає активних переміщень.")
        return

    # Відсортовано від старих до нових за ID
    ordered_ids = sorted(transfers.keys(), key=_id_sort_key)

    # Лишаємо активні
    active_ids = [tid for tid in ordered_ids if not transfers[tid].get("done")]
    if not active_ids:
        await message.answer("🔕 У вас немає активних переміщень.")
        return

    text = "<b>🔀 Активні переміщення:</b>\n\n"
    for tid in active_ids:
        t = transfers[tid]
        text += (
            f"🆔 {t['id']}\n"
            f"📤 {t['sender']['name']} ➡️ 📥 {t['receiver']['name']}\n\n"
        )

    text += "🔽 Введіть ID переміщення, яке хочете обрати:"
    await message.answer(text)
    await state.set_state(SelectFSM.waiting_for_id)


@router.message(SelectFSM.waiting_for_id, F.text)
async def receive_transfer_id(message: Message, state: FSMContext):
    operator_id = message.from_user.id
    input_id = message.text.strip().upper()

    transfers = get_transfers(operator_id)  # dict: {id: transfer}

    if input_id not in transfers:
        await message.answer("❗ Таке ID не знайдено серед ваших переміщень.")
        return

    if transfers[input_id].get("done"):
        await message.answer("⚠️ Це переміщення вже завершено. Оберіть активне.")
        return

    # ✅ Зберігаємо вибране активне переміщення
    active_transfers[operator_id] = input_id

    await message.answer(f"✅ Обрано переміщення <b>{input_id}</b> як активне.")

    # ✅ Дублюємо накладну оператору
    await send_transfer_copy(message.bot, operator_id, input_id)

    await state.clear()
