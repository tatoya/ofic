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


BOT_TOKEN = os.getenv("BOT_TOKEN")
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

# Клавиатура
guest_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛎️ Позвать официанта")],
        [KeyboardButton(text="💰 Рассчитать счёт")]
    ],
    resize_keyboard=True
)

# ========== ОБРАБОТЧИКИ ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    logging.info(f"Команда /start от {message.from_user.id}")
    
    args = message.text.split()
    
    if len(args) > 1 and args[1] in tables_db:
        table = tables_db[args[1]]
        user_table[message.from_user.id] = table
        await message.answer(
            f"🍽️ Добро пожаловать, стол {table}!\n\nВыберите действие:",
            reply_markup=guest_kb
        )
    else:
        await message.answer("❌ Отсканируйте QR-код со стола")

@dp.message(lambda msg: msg.text == "🛎️ Позвать официанта")
async def call_waiter(message: types.Message):
    table = user_table.get(message.from_user.id)
    if table:
        await bot.send_message(
            ADMIN_CHAT_ID, 
            f"🛎️ ВЫЗОВ ОФИЦИАНТА — Стол {table}"
        )
        await message.answer("✅ Официант уже уведомлён")
    else:
        await message.answer("❌ Ошибка: не определён стол")

@dp.message(lambda msg: msg.text == "💰 Рассчитать счёт")
async def ask_bill(message: types.Message):
    table = user_table.get(message.from_user.id)
    if table:
        await bot.send_message(
            ADMIN_CHAT_ID, 
            f"💰 СЧЁТ — Стол {table}"
        )
        await message.answer("✅ Официант принесёт счёт")
    else:
        await message.answer("❌ Ошибка: не определён стол")

@dp.message(Command("add_table"))
async def add_table(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    try:
        _, payload, num = message.text.split()
        tables_db[payload] = int(num)
        save_tables(tables_db)
        await message.reply(f"✅ Стол {num} привязан к QR-коду: {payload}")
    except:
        await message.reply("❌ Использование: /add_table qr123 12")

@dp.message(Command("tables"))
async def list_tables(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    if not tables_db:
        await message.reply("Нет привязанных столов")
        return
    text = "📋 Столы:\n" + "\n".join([f"{k} → {v}" for k, v in tables_db.items()])
    await message.reply(text)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот запущен на Bothost")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())