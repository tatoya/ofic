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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_tables = {}
waiting_for_table = {}

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛎️ Позвать официанта")],
        [KeyboardButton(text="💰 Рассчитать счёт")]
    ],
    resize_keyboard=True
)
@dp.message(Command("getid"))
async def get_id(message: types.Message):
    await message.answer(f"ID этого чата: `{message.chat.id}`", parse_mode="Markdown")
@dp.message(Command("start"))
async def start(message: types.Message):
    waiting_for_table[message.from_user.id] = True
    await message.answer(
        "🍽️ Добро пожаловать!\n\nВведите номер вашего стола:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
    )

@dp.message(lambda msg: msg.text == "❌ Отмена")
async def cancel(message: types.Message):
    waiting_for_table.pop(message.from_user.id, None)
    user_tables.pop(message.from_user.id, None)
    await message.answer("Отменено. Отправьте /start", reply_markup=ReplyKeyboardRemove())

@dp.message(lambda msg: waiting_for_table.get(msg.from_user.id, False))
async def get_table(message: types.Message):
    try:
        table_num = int(message.text)
        user_tables[message.from_user.id] = table_num
        waiting_for_table.pop(message.from_user.id, None)
        await message.answer(
            f"🍽️ Стол №{table_num}\n\nВыберите действие:",
            reply_markup=main_kb
        )
    except ValueError:
        await message.answer("Введите номер стола цифрами.")

@dp.message(lambda msg: msg.text == "🛎️ Позвать официанта")
async def call_waiter(message: types.Message):
    table = user_tables.get(message.from_user.id)
    if not table:
        await message.answer("Сначала /start и номер стола")
        return
    await bot.send_message(ADMIN_CHAT_ID, f"🛎️ ВЫЗОВ ОФИЦИАНТА — Стол {table}")
    await message.answer(f"✅ Официант уведомлён!")

@dp.message(lambda msg: msg.text == "💰 Рассчитать счёт")
async def ask_bill(message: types.Message):
    table = user_tables.get(message.from_user.id)
    if not table:
        await message.answer("Сначала /start и номер стола")
        return
    await bot.send_message(ADMIN_CHAT_ID, f"💰 ЗАПРОС СЧЁТА — Стол {table}")
    await message.answer(f"✅ Счёт принесут!")

@dp.message(Command("reset"))
async def reset(message: types.Message):
    user_tables.pop(message.from_user.id, None)
    waiting_for_table.pop(message.from_user.id, None)
    await message.answer("Сброшено. Отправьте /start", reply_markup=ReplyKeyboardRemove())

async def main():
    print("🚀 Бот запущен")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
