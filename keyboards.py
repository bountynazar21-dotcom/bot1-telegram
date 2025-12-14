from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import CITY_GROUPS
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 📍 Кнопки груп
def group_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=key)] for key in CITY_GROUPS.keys()],
        resize_keyboard=True
    )

# 🏪 Кнопки точок
def point_keyboard(group):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=p['name'])] for p in CITY_GROUPS[group]],
        resize_keyboard=True
    )

# ✅ Кнопка підтвердження точок
confirmation_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Підтвердити точки")],
        [KeyboardButton(text="❌ Скасувати")]
    ],
    resize_keyboard=True
)

# 📸 Почати надсилання
upload_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📸 Почати надсилання")],
        [KeyboardButton(text="❌ Скасувати")]
    ],
    resize_keyboard=True
)

# 📦 Завершити надсилання + інші кнопки для завершення (✏️ Коригування видалено)
combined_finish_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 Завершити надсилання")],
        [KeyboardButton(text="❌ Скасувати")]
    ],
    resize_keyboard=True
)

# ✅ / 📬 підтвердження точками + 🛠 коригування
point_confirm_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Віддав товар"), KeyboardButton(text="📬 Отримав товар")],
    ],
    resize_keyboard=True
)

# ❌ Скасування
cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Скасувати")]],
    resize_keyboard=True
)

# 🎛 Клавіатура дій для старту / оператора
action_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Вибрати відправника"), KeyboardButton(text="📥 Вибрати отримувача")],
        [KeyboardButton(text="❌ Скасувати")]
    ],
    resize_keyboard=True
)

def correction_keyboard(transfer_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Надіслати нову накладну", callback_data=f"resend:{transfer_id}")]
        ]
    )
