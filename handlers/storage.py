# storage.py — глобальні тимчасові сховища для логіки бота

# Основне сховище переміщень
# Структура:
# {
#     operator_id: {
#         transfer_id_1: {...},
#         transfer_id_2: {...}
#     }
# }
status_tracker = {}

# Поточне активне переміщення для кожного оператора
# Структура:
# {
#     operator_id: transfer_id
# }
current_transfer_id = {}

# Тимчасове сховище для коригувань
# Структура:
# {
#     operator_id: transfer_id
# }
pending_corrections = {}

# Активні переміщення
active_transfers = {}
