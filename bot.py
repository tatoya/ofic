import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

logging.basicConfig(level=logging.INFO)

# ========== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
# =========================================

# Проверка переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан")
if not ADMIN_CHAT_ID:
    raise ValueError("ADMIN_CHAT_ID не задан")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилища
user_tables = {}
waiting_for_table = {}

# Клавиатуры
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛎️ Позвать официанта")],
        [KeyboardButton(text="💰 Рассчитать счёт")]
    ],
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)

# ========== КОМАНДА /getid (ВРЕМЕННАЯ) ==========
@dp.message(Command("getid"))
async def get_chat_id(message: types.Message):
    """Узнать ID текущего чата"""
    await message.answer(
        f"📌 ID этого чата:\n`{message.chat.id}`",
        parse_mode="Markdown"
    )

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
@dp.message(Command("start"))
async def start(message: types.Message):
    waiting_for_table[message.from_user.id] = True
    await message.answer(
        "🍽️ Добро пожаловать!\n\nВведите номер вашего стола:",
        reply_markup=cancel_kb
    )

@dp.message(lambda msg: msg.text == "❌ Отмена")
async def cancel(message: types.Message):
    waiting_for_table.pop(message.from_user.id, None)
    user_tables.pop(message.from_user.id, None)
    await message.answer("❌ Отменено. Отправьте /start для начала.", reply_markup=ReplyKeyboardRemove())

@dp.message(lambda msg: waiting_for_table.get(msg.from_user.id, False))
async def get_table(message: types.Message):
    try:
        table_num = int(message.text.strip())
        if table_num < 1 or table_num > 100:
            await message.answer("Номер стола должен быть от 1 до 100. Попробуйте ещё раз:")
            return
        
        user_tables[message.from_user.id] = table_num
        waiting_for_table.pop(message.from_user.id, None)
        await message.answer(
            f"🍽️ Стол №{table_num}\n\nВыберите действие:",
            reply_markup=main_kb
        )
    except ValueError:
        await message.answer("Пожалуйста, введите номер стола цифрами. Например: 12")

@dp.message(lambda msg: msg.text == "🛎️ Позвать официанта")
async def call_waiter(message: types.Message):
    table = user_tables.get(message.from_user.id)
    if not table:
        await message.answer("❌ Сначала отправьте /start и укажите номер стола.")
        return
    
    try:
        await bot.send_message(ADMIN_CHAT_ID, f"🛎️ ВЫЗОВ ОФИЦИАНТА — Стол {table}")
        await message.answer(f"✅ Официант уведомлён о вызове со стола {table}!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: не удалось отправить уведомление. Сообщите официанту лично.")
        print(f"Ошибка отправки: {e}")

@dp.message(lambda msg: msg.text == "💰 Рассчитать счёт")
async def ask_bill(message: types.Message):
    table = user_tables.get(message.from_user.id)
    if not table:
        await message.answer("❌ Сначала отправьте /start и укажите номер стола.")
        return
    
    try:
        await bot.send_message(ADMIN_CHAT_ID, f"💰 ЗАПРОС СЧЁТА — Стол {table}")
        await message.answer(f"✅ Официант принесёт счёт на стол {table}.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: не удалось отправить запрос. Сообщите официанту лично.")
        print(f"Ошибка отправки: {e}")

@dp.message(Command("reset"))
async def reset(message: types.Message):
    user_tables.pop(message.from_user.id, None)
    waiting_for_table.pop(message.from_user.id, None)
    await message.answer("🔄 Стол сброшен. Отправьте /start, чтобы начать заново.", reply_markup=ReplyKeyboardRemove())

# ========== ЗАПУСК БОТА ==========
async def main():
    print("🚀 Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook очищен")
    me = await bot.get_me()
    print(f"✅ Бот @{me.username} готов к работе!")
    print(f"📌 ADMIN_CHAT_ID = {ADMIN_CHAT_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
