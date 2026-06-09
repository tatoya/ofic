import asyncio
import json
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# ========== НАСТРОЙКИ ==========
# 👇👇👇 ЗАМЕНИТЕ НА ВАШ ТОКЕН 👇👇👇
BOT_TOKEN = os.getenv("BOT_TOKEN")
# 👇👇👇 ID ГРУППЫ ОФИЦИАНТОВ (отрицательное число) 👇👇👇
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
# ================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Файл для хранения столов
TABLES_FILE = "tables.json"

def load_tables():
    if os.path.exists(TABLES_FILE):
        with open(TABLES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_tables(tables):
    with open(TABLES_FILE, "w", encoding="utf-8") as f:
        json.dump(tables, f, indent=2, ensure_ascii=False)

tables_db = load_tables()
user_table = {}

# Клавиатура для гостя
guest_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛎️ Позвать официанта")],
        [KeyboardButton(text="💰 Рассчитать счёт")]
    ],
    resize_keyboard=True
)

# ========== ОБРАБОТЧИКИ КОМАНД ==========

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    logging.info(f"Команда /start от {message.from_user.id}")
    
    # Разбираем аргументы (то, что после start=)
    args = message.text.split()
    
    if len(args) > 1:
        payload = args[1]  # Например, "table_12"
        if payload in tables_db:
            table_num = tables_db[payload]
            user_table[message.from_user.id] = table_num
            await message.answer(
                f"🍽️ Добро пожаловать, стол {table_num}!\n\nВыберите действие:",
                reply_markup=guest_kb
            )
            return
    
    # Если QR-код не распознан или его нет
    await message.answer(
        "❌ Пожалуйста, отсканируйте QR-код на вашем столе.\n\n"
        "Если вы уже отсканировали QR-код, убедитесь, что ссылка ведёт на этого бота."
    )

# Кнопка "Позвать официанта"
@dp.message(lambda msg: msg.text == "🛎️ Позвать официанта")
async def call_waiter(message: types.Message):
    logging.info(f"Нажата кнопка вызова от {message.from_user.id}")
    
    table = user_table.get(message.from_user.id)
    if not table:
        await message.answer("❌ Ошибка: не определён стол. Пожалуйста, отсканируйте QR-код заново.")
        return
    
    # Отправляем уведомление в группу официантов
    try:
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"🛎️ ВЫЗОВ ОФИЦИАНТА\n\nСтол №{table}\nГость: @{message.from_user.username if message.from_user.username else 'без юзернейма'}"
        )
        await message.answer("✅ Официант уже уведомлён! Пожалуйста, подождите минуту.")
    except Exception as e:
        logging.error(f"Ошибка отправки в группу: {e}")
        await message.answer("⚠️ Не удалось уведомить официанта. Пожалуйста, позовите официанта голосом.")

# Кнопка "Рассчитать счёт"
@dp.message(lambda msg: msg.text == "💰 Рассчитать счёт")
async def ask_bill(message: types.Message):
    logging.info(f"Нажата кнопка счёта от {message.from_user.id}")
    
    table = user_table.get(message.from_user.id)
    if not table:
        await message.answer("❌ Ошибка: не определён стол. Пожалуйста, отсканируйте QR-код заново.")
        return
    
    # Отправляем запрос в группу официантов
    try:
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"💰 ЗАПРОС СЧЁТА\n\nСтол №{table}\nГость: @{message.from_user.username if message.from_user.username else 'без юзернейма'}"
        )
        await message.answer("✅ Официант принесёт счёт через минуту.")
    except Exception as e:
        logging.error(f"Ошибка отправки в группу: {e}")
        await message.answer("⚠️ Не удалось передать запрос. Пожалуйста, позовите официанта.")

# ========== КОМАНДА /add_table (БЕЗ ПРОВЕРКИ ГРУППЫ) ==========
# Работает из ЛЮБОГО чата — личного, группы, куда угодно
@dp.message(Command("add_table"))
async def add_table(message: types.Message):
    logging.info(f"Команда add_table от {message.from_user.id}, чат: {message.chat.id}")
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.reply("❌ Использование: /add_table qr123 12\n\nПример: /add_table table_1 1")
            return
        
        _, payload, num = parts
        tables_db[payload] = int(num)
        save_tables(tables_db)
        await message.reply(f"✅ Стол {num} привязан к QR-коду: {payload}")
        logging.info(f"Привязка добавлена: {payload} -> {num}")
    except ValueError:
        await message.reply("❌ Ошибка: номер стола должен быть числом\nПример: /add_table table_1 1")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")
        logging.error(f"Ошибка add_table: {e}")

# Команда /tables (список всех столов)
@dp.message(Command("tables"))
async def list_tables(message: types.Message):
    logging.info(f"Команда tables от {message.from_user.id}")
    
    if not tables_db:
        await message.reply("📭 Нет привязанных столов\n\nДобавьте первый: /add_table table_1 1")
        return
    
    text = "📋 Привязанные столы:\n\n"
    for payload, num in tables_db.items():
        text += f"• {payload} → стол {num}\n"
    
    await message.reply(text)

# Команда /help
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.reply(
        "📖 **Команды бота:**\n\n"
        "**Для админов:**\n"
        "/add_table [код] [номер] — привязать QR-код к столу\n"
        "/tables — показать все привязанные столы\n\n"
        "**Пример:**\n"
        "/add_table table_1 1\n\n"
        "**Для гостей:**\n"
        "Отсканируйте QR-код на столе"
    )

# Обработчик всех остальных сообщений (для отладки)
@dp.message()
async def catch_all(message: types.Message):
    # Игнорируем, просто логируем
    logging.info(f"Получено сообщение: {message.text}")

# ========== ЗАПУСК БОТА ==========
async def main():
    print("=" * 40)
    print("🚀 ЗАПУСК БОТА")
    print("=" * 40)
    
    # Очищаем вебхук (важно для работы)
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook очищен")
    
    # Выводим информацию о боте
    me = await bot.get_me()
    print(f"✅ Бот: @{me.username}")
    print(f"✅ ID бота: {me.id}")
    print(f"✅ Группа для уведомлений: {ADMIN_CHAT_ID}")
    print("=" * 40)
    print("🎯 Бот готов к работе!")
    print("📱 Команды:")
    print("   /start - проверить работу")
    print("   /add_table table_1 1 - привязать стол")
    print("   /tables - посмотреть привязанные столы")
    print("=" * 40)
    
    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
