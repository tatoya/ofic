import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
# ================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояние: ждём ввод номера стола
class TableState(StatesGroup):
    waiting_for_table = State()

# Словарь: user_id -> номер стола
user_table = {}

# Клавиатура после ввода стола
guest_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛎️ Позвать официанта")],
        [KeyboardButton(text="💰 Рассчитать счёт")]
    ],
    resize_keyboard=True
)

# Клавиатура с кнопкой отмены
cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)

# ========== ОБРАБОТЧИКИ ==========

# Команда /start — просим ввести номер стола
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(TableState.waiting_for_table)
    await message.answer(
        "🍽️ **Добро пожаловать!**\n\n"
        "Введите **номер вашего стола** цифрами.\n"
        "Например: `12`",
        parse_mode="Markdown",
        reply_markup=cancel_kb
    )

# Обработка ввода номера стола
@dp.message(TableState.waiting_for_table)
async def process_table_number(message: types.Message, state: FSMContext):
    # Если нажали "Отмена"
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Ввод отменён. Чтобы начать заново, отправьте /start",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Проверяем, что введено число
    try:
        table_num = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите **число** — номер вашего стола.")
        return
    
    # Сохраняем номер стола
    user_table[message.from_user.id] = table_num
    await state.clear()
    
    await message.answer(
        f"🍽️ **Стол №{table_num}**\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=guest_kb
    )

# Кнопка вызова официанта
@dp.message(lambda msg: msg.text == "🛎️ Позвать официанта")
async def call_waiter(message: types.Message):
    table = user_table.get(message.from_user.id)
    if not table:
        await message.answer("❌ Сначала отправьте /start и укажите номер стола.")
        return
    
    username = f"@{message.from_user.username}" if message.from_user.username else "гость"
    await bot.send_message(
        ADMIN_CHAT_ID,
        f"🛎️ **ВЫЗОВ ОФИЦИАНТА**\n\nСтол №{table}\nГость: {username}"
    )
    await message.answer(f"✅ Официант уже уведомлён о вызове со стола №{table}!")

# Кнопка запроса счёта
@dp.message(lambda msg: msg.text == "💰 Рассчитать счёт")
async def ask_bill(message: types.Message):
    table = user_table.get(message.from_user.id)
    if not table:
        await message.answer("❌ Сначала отправьте /start и укажите номер стола.")
        return
    
    username = f"@{message.from_user.username}" if message.from_user.username else "гость"
    await bot.send_message(
        ADMIN_CHAT_ID,
        f"💰 **ЗАПРОС СЧЁТА**\n\nСтол №{table}\nГость: {username}"
    )
    await message.answer(f"✅ Счёт принесут на стол №{table} через минуту.")

# Команда /reset — сбросить стол
@dp.message(Command("reset"))
async def reset_table(message: types.Message, state: FSMContext):
    if message.from_user.id in user_table:
        del user_table[message.from_user.id]
    await state.clear()
    await message.answer(
        "🔄 Стол сброшен. Отправьте /start, чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )

# Команда /help
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 **Как пользоваться:**\n\n"
        "1. Отправьте /start\n"
        "2. Введите номер стола\n"
        "3. Выберите действие\n\n"
        "Если ошиблись столом — /reset"
    )

# Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Бот запущен (упрощённая версия)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
