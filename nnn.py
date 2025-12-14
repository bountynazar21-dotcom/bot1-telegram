import asyncio
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BOT_TOKEN, OPERATORS, DB_PATH
from handlers.db import init_db  # важливо: delete_old_transfers зі старту НЕ викликаємо
from handlers.loader import load_transfers_from_db
from handlers.storage import status_tracker  # {operator_id: {transfer_id: {...}}}

# ✅ Імпорт router-ів
from handlers.base import router as base_router
from handlers.upload import router as upload_router
from handlers.confirm import router as confirm_router
from handlers.confirm_and_correction import router as correction_router

from commands.select_transfer import router as select_router
from commands.report import router as report_router
from commands.finish import router as finish_router
from commands.list_done import router as list_router
from commands.clear_done import router as clear_router
from commands.correction import router as correction_command_router
from commands.select_point_transfer import router as point_select_router
from commands.cleardb import router as cleardb_router


# ✅ Налаштування логів
logging.basicConfig(level=logging.INFO)

# ✅ Ініціалізація сховища
storage = MemoryStorage()

# ✅ Ініціалізація бота
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# ✅ Ініціалізація Dispatcher
dp = Dispatcher(storage=storage)

# ✅ Підключення router-ів
dp.include_router(base_router)
dp.include_router(upload_router)
dp.include_router(confirm_router)
dp.include_router(correction_router)
dp.include_router(select_router)
dp.include_router(report_router)
dp.include_router(finish_router)
dp.include_router(list_router)
dp.include_router(clear_router)
dp.include_router(correction_command_router)
dp.include_router(point_select_router)
dp.include_router(cleardb_router)

# ✅ Команди бота
bot_commands = [
    BotCommand(command="start", description="🔁 Почати знову"),
    BotCommand(command="mytransfers", description="📋 Обрати своє активне переміщення"),
    BotCommand(command="correction", description="🛠 Почати коригування"),
    BotCommand(command="finish", description="✅ Завершити переміщення"),
    BotCommand(command="list", description="📦 Список завершених переміщень"),
    BotCommand(command="clear", description="🧹 Очистити завершені переміщення"),
    BotCommand(command="select", description="🔀 Обрати переміщення за ID"),
    BotCommand(command="report", description="📊 Звіт по переміщенню"),
    BotCommand(command="cleardb", description="🗑 Очистити БД без обнулення ID"),
]

# ✅ Функція-робота для нагадування точкам
# ✅ Розумне нагадування тільки тим, хто ще не зробив дію
async def notify_points_about_open_transfers():
    logging.info("🔔 Виконується задача нагадування точкам...")

    for operator_id, transfers in list(status_tracker.items()):
        if not transfers:
            continue

        for transfer in list(transfers.values()):
            try:
                if transfer.get("done"):
                    continue  # вже закрито

                sender = transfer.get("sender", {}) or {}
                receiver = transfer.get("receiver", {}) or {}
                transfer_id = transfer.get("id", "—")

                sender_ok = bool(transfer.get("sender_ok"))
                receiver_ok = bool(transfer.get("receiver_ok"))

                # Кому нагадуємо
                notify_sender = not sender_ok and sender.get("id")
                notify_receiver = not receiver_ok and receiver.get("id")

                # Якщо нікому — скіп
                if not notify_sender and not notify_receiver:
                    continue

                # 🔔 Відправнику (якщо він ще не підтвердив видачу)
                if notify_sender:
                    try:
                        await bot.send_message(
                            sender["id"],
                            (
                                "🔔 Нагадування!\n"
                                "У вас є відкрите переміщення, яке очікує видачу:\n\n"
                                f"🆔 {transfer_id}\n"
                                f"📥 Отримувач: {receiver.get('name', '—')}\n\n"
                                "Будь ласка, підтвердіть видачу або зверніться до оператора."
                            )
                        )
                    except Exception as e:
                        logging.warning(f"⚠️ Не вдалося надіслати повідомлення відправнику: {e}")

                # 🔔 Отримувачу (якщо він ще не підтвердив отримання)
                if notify_receiver:
                    try:
                        await bot.send_message(
                            receiver["id"],
                            (
                                "🔔 Нагадування!\n"
                                "У вас є відкрите переміщення, яке очікує підтвердження отримання:\n\n"
                                f"🆔 {transfer_id}\n"
                                f"📤 Відправник: {sender.get('name', '—')}\n\n"
                                "Будь ласка, підтвердіть отримання або зверніться до оператора."
                            )
                        )
                    except Exception as e:
                        logging.warning(f"⚠️ Не вдалося надіслати повідомлення отримувачу: {e}")

            except Exception as e:
                logging.exception(f"❌ Помилка під час обробки transfer {transfer.get('id')}: {e}")

    logging.info("✅ Завершено нагадування точкам.")

# ... усередині main()
async def main():
    # 1) Підняти БД
    init_db()
    logging.info(f"📦 DB_PATH = {DB_PATH}")

    # 2) Завантажити активні переміщення у статус-трекер
    load_transfers_from_db()

    # 3) Ініціалізувати шедулер
    kyiv_tz = ZoneInfo("Europe/Kyiv")
    scheduler = AsyncIOScheduler(timezone=kyiv_tz)

    trigger = CronTrigger(
        day_of_week="fri",
        hour=10,
        minute=0,
        timezone=kyiv_tz
    )

    scheduler.add_job(
        notify_points_about_open_transfers,
        trigger=trigger,
        id="notify_open_transfers_friday_10",
        replace_existing=True
    )

    scheduler.start()
    logging.info("🗓 Шедулер стартував.")

    # 4) Команди бота + старт поллінгу
    print("✅ Бот запущено. Очікування команд...")
    await bot.set_my_commands(bot_commands)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

    # 5) Акуратно зупиняємо шедулер перед виходом
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logging.info("🛑 Шедулер зупинено.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Бот зупинено вручну.")

