from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.enums import ParseMode
import asyncio
from io import StringIO

from handlers.db import get_transfers
from config import OPERATORS

router = Router()

# Безпечна межа трохи менша за 4096 (щоб не впертись у ліміт з емодзі/HTML)
MAX_TG_LEN = 3900

def format_item(tr: dict) -> str:
    return (
        f"🆔 <b>{tr['id']}</b>\n"
        f"📤 Відправник: {tr['sender']['name']}\n"
        f"📥 Отримувач: {tr['receiver']['name']}\n"
        f"🔄 Статуси:\n"
        f" ├ Відав товар: {'✅' if tr['sender_ok'] else '❌'}\n"
        f" └ Отримав товар: {'✅' if tr['receiver_ok'] else '❌'}\n"
    )

async def send_section(message: Message, title: str, items: list[str]):
    """Шле секцію (заголовок + елементи) кількома повідомленнями, не перевищуючи ліміт."""
    if not items:
        return
    batch = title + "\n\n"
    for item in items:
        # Якщо наступний елемент переповнює — відправляємо поточну порцію
        if len(batch) + len(item) + 2 > MAX_TG_LEN:
            await message.answer(batch.strip(), parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.05)  # мікропаузa, щоб не впертись у rate limit
            batch = title + "\n\n"  # нова порція починається з заголовка
        batch += ("" if batch.endswith("\n\n") else "\n") + item

    if batch:
        await message.answer(batch.strip(), parse_mode=ParseMode.HTML)

def count_batches(items: list[str]) -> int:
    """Груба оцінка кількості батчів для прийняття рішення про .txt."""
    if not items:
        return 0
    total_len = sum(len(i) + 1 for i in items)  # + \n
    # + довжина заголовка, але для оцінки не критично
    return max(1, (total_len // MAX_TG_LEN) + 1)

@router.message(F.text == "/report")
async def report_command(message: Message):
    operator_id = message.from_user.id

    if operator_id not in OPERATORS:
        await message.answer("🚫 Ця команда доступна лише для операторів.")
        return

    transfers = get_transfers(operator_id)

    if not transfers:
        await message.answer("📭 У вас ще немає жодного переміщення.")
        return

    active_items: list[str] = []
    done_items: list[str] = []

    for tr in transfers.values():
        (done_items if tr.get("done") else active_items).append(format_item(tr))

    # 1) Надсилаємо секції батчами
    await send_section(message, "<b>🔸 Активні переміщення:</b>", active_items)
    await send_section(message, "<b>🟩 Завершені переміщення:</b>", done_items)

    # 2) Якщо повідомлень забагато — додаємо повний звіт файлом .txt
    total_batches = count_batches(active_items) + count_batches(done_items)
    if total_batches >= 8:
        buf = StringIO()
        if active_items:
            buf.write("🔸 Активні переміщення:\n\n")
            buf.write("\n".join([i.replace("<b>", "").replace("</b>", "") for i in active_items]))
            buf.write("\n\n")
        if done_items:
            buf.write("🟩 Завершені переміщення:\n\n")
            buf.write("\n".join([i.replace("<b>", "").replace("</b>", "") for i in done_items]))

        data = buf.getvalue().encode("utf-8")
        await message.answer_document(
            BufferedInputFile(data, filename="report.txt"),
            caption="📎 Повний звіт у файлі.",
        )
