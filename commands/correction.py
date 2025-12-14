from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from states import CorrectionFSM
from handlers.db import get_transfers
from handlers.storage import active_transfers
from config import OPERATORS
from keyboards import correction_keyboard

router = Router()

@router.message(F.text.casefold() == "/correction")
async def start_correction(message: Message, state: FSMContext):
    user_id = message.from_user.id

    # ✅ Чи є активне переміщення для точки
    transfer_id = active_transfers.get(user_id)
    if not transfer_id:
        await message.answer(
            "⚠️ У вас не обрано активного переміщення.\n"
            "Скористайтесь спершу командою /mytransfers, щоб обрати потрібне переміщення."
        )
        return

    # ✅ Знайти operator_id, де збережено це переміщення
    for operator_id in OPERATORS:
        transfers = get_transfers(operator_id)
        if transfer_id in transfers:
            await state.set_state(CorrectionFSM.waiting_text)
            await state.update_data(
                operator_id=operator_id,
                transfer_id=transfer_id
            )
            await message.answer(
                f"✏️ Напишіть текст коригування для переміщення, має бути вказаний код товару кількість якої не вистачає ,або більше #{transfer_id}:"
            )
            return

    await message.answer(
        f"❌ Не знайдено переміщення #{transfer_id}. Можливо, воно вже завершене або видалене."
    )


@router.message(CorrectionFSM.waiting_text)
async def receive_correction_text(message: Message, state: FSMContext):
    data = await state.get_data()
    operator_id = data["operator_id"]
    transfer_id = data["transfer_id"]

    correction_text = message.text

    # ✅ Отримуємо переміщення з БД
    transfers = get_transfers(operator_id)
    transfer = transfers.get(transfer_id)

    if not transfer:
        await message.answer("❌ Переміщення не знайдено.")
        await state.clear()
        return

    sender = transfer["sender"]
    receiver = transfer["receiver"]

    sender_id = sender["id"]
    point_role = (
        "ВІДПРАВНИК"
        if message.from_user.id == sender_id
        else "ОТРИМУВАЧ"
    )

    await message.bot.send_message(
        operator_id,
        f"🛠 Запит на коригування по переміщенню <b>#{transfer_id}</b>:\n\n"
        f"📤 <b>Відправник:</b> {sender['name']}\n"
        f"📥 <b>Отримувач:</b> {receiver['name']}\n"
        f"👤 <b>Повідомлення від:</b> {point_role} "
        f"({message.from_user.full_name}, ID: <code>{message.from_user.id}</code>)\n\n"
        f"📝 <i>{correction_text}</i>",
        reply_markup=correction_keyboard(transfer_id)
    )

    await message.answer("✅ Ваше повідомлення надіслано оператору.")
    await state.clear()

