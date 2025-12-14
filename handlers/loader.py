# handlers/loader.py

from handlers.db import get_transfers
from handlers.storage import status_tracker
from config import OPERATORS

def load_transfers_from_db():
    """
    Підвантажує всі переміщення з БД у status_tracker при запуску бота.
    """
    for operator_id in OPERATORS:
        transfers = get_transfers(operator_id)
        if not transfers:
            continue

        for transfer_id, tr in transfers.items():
            # Якщо переміщення вже завершено — не вантажимо його у RAM
            if tr.get("done"):
                continue

            status_tracker.setdefault(operator_id, {})[transfer_id] = {
                "id": tr["id"],
                "sender": tr["sender"],
                "receiver": tr["receiver"],
                "photos": tr["photos"],
                "captions": tr["captions"],
                "sender_ok": tr["sender_ok"],
                "receiver_ok": tr["receiver_ok"],
                "done": tr["done"],
                "reason": tr["reason"],
            }
