import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)

# ========== НАСТРОЙКИ (ВСТАВЬТЕ СВОИ ЗНАЧЕНИЯ) ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
# =========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    waiting_for_table = State()

user_tables = {}

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

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.set_state(Form.waiting_for_table)
    await message.answer("🍽️ Добро пожаловать!\n\nВведите номер вашего стола:", reply_markup=cancel_kb)

@dp.message(Form.waiting_for_table)
async def get_table(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено. Отправьте /start для начала.", reply_markup=types.ReplyKeyboardRemove())
        return
    
    try:
        table_num = int(message.text)
        user_tables[message.from_user.id] = table_num
        await state.clear()
        await message.answer(f"🍽️ Стол №{table_num}\n\nВыберите действие:", reply_markup=main_kb)
    except ValueError:
        await message.answer("Пожалуйста, введите номер стола цифрами.")

@dp.message(lambda m: m.text == "🛎️ Позвать официанта")
async def call_waiter(message: types.Message):
    table = user_tables.get(message.from_user.id)
    if not table:
        await message.answer("Сначала отправьте /start и укажите номер стола.")
        return
    await bot.send_message(ADMIN_CHAT_ID, f"🛎️ ВЫЗОВ ОФИЦИАНТА — Стол {table}")
    await message.answer(f"✅ Официант уведомлён о вызове со стола {table}!")

@dp.message(lambda m: m.text == "💰 Рассчитать счёт")
async def ask_bill(message: types.Message):
    table = user_tables.get(message.from_user.id)
    if not table:
        await message.answer("Сначала отправьте /start и укажите номер стола.")
        return
    await bot.send_message(ADMIN_CHAT_ID, f"💰 ЗАПРОС СЧЁТА — Стол {table}")
    await message.answer(f"✅ Счёт принесут на стол {table}.")

@dp.message(Command("reset"))
async def reset(message: types.Message, state: FSMContext):
    if message.from_user.id in user_tables:
        del user_tables[message.from_user.id]
    await state.clear()
    await message.answer("Стол сброшен. Отправьте /start.", reply_markup=types.ReplyKeyboardRemove())

async def main():
    print("Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    print("Webhook очищен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
