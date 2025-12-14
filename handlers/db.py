import sqlite3
import json
from datetime import datetime
from config import DB_PATH

def init_db():
    """
    Створює таблиці transfers і counter, якщо вони ще не існують.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Таблиця transfers
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transfers (
            transfer_id TEXT PRIMARY KEY,
            operator_id INTEGER,
            sender_point_name TEXT,
            sender_point_id INTEGER,
            receiver_point_name TEXT,
            receiver_point_id INTEGER,
            photos TEXT,
            captions TEXT,
            sender_ok INTEGER,
            receiver_ok INTEGER,
            done INTEGER,
            reason TEXT,
            created_at TEXT
        )
    """)

    # Таблиця counter
    cur.execute("""
        CREATE TABLE IF NOT EXISTS counter (
            id TEXT PRIMARY KEY,
            value INTEGER
        )
    """)

    conn.commit()
    conn.close()


def generate_transfer_id():
    """
    Генерує новий transfer_id, який не обнуляється після перезапуску.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Читаємо поточне значення
    cur.execute("""
        SELECT value FROM counter WHERE id = 'transfer_id'
    """)
    result = cur.fetchone()

    if result:
        current_id = result[0] + 1
        cur.execute("""
            UPDATE counter
            SET value = ?
            WHERE id = 'transfer_id'
        """, (current_id,))
    else:
        current_id = 1
        cur.execute("""
            INSERT INTO counter (id, value) VALUES ('transfer_id', ?)
        """, (current_id,))

    conn.commit()
    conn.close()

    return str(current_id)


def save_transfer(
    transfer_id,
    operator_id,
    sender,
    receiver,
    photos,
    captions,
    sender_ok,
    receiver_ok,
    done,
    reason
):
    """
    Зберігає або оновлює переміщення в БД.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO transfers
        (transfer_id, operator_id,
         sender_point_name, sender_point_id,
         receiver_point_name, receiver_point_id,
         photos, captions, sender_ok, receiver_ok, done, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        transfer_id,
        operator_id,
        sender.get("name"),
        sender.get("id"),
        receiver.get("name"),
        receiver.get("id"),
        json.dumps(photos),
        json.dumps(captions),
        int(sender_ok),
        int(receiver_ok),
        int(done),
        reason,
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()


def get_transfers(operator_id):
    """
    Повертає всі переміщення для даного оператора у вигляді словника.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM transfers
        WHERE operator_id = ?
    """, (operator_id,))

    rows = cur.fetchall()
    conn.close()

    transfers = {}
    for row in rows:
        transfer_id = row[0]
        transfers[transfer_id] = {
            "id": transfer_id,
            "sender": {
                "name": row[2],
                "id": row[3],
            },
            "receiver": {
                "name": row[4],
                "id": row[5],
            },
            "photos": json.loads(row[6]) if row[6] else [],
            "captions": json.loads(row[7]) if row[7] else [],
            "sender_ok": bool(row[8]),
            "receiver_ok": bool(row[9]),
            "done": bool(row[10]),
            "reason": row[11],
            "created_at": row[12]
        }
    return transfers


def delete_old_transfers():
    """
    Видаляє переміщення, старші за 14 днів.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM transfers
        WHERE datetime(created_at) < datetime('now', '-14 days')
    """)
    conn.commit()
    conn.close()


def delete_transfer_by_id(transfer_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM transfers WHERE transfer_id = ?",
        (transfer_id,)
    )
    conn.commit()
    conn.close()
    
def clear_transfers_but_keep_counter():
    """
    Видаляє всі переміщення з БД, але не скидає лічильник transfer_id.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Просто очищаємо таблицю transfers
    cur.execute("DELETE FROM transfers")

    conn.commit()
    conn.close()