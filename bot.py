import asyncio
import json
import os
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

# Состояния для FSM (машина состояний)
class TableState(StatesGroup):
    waiting_for_table = State()  # Ждём ввод номера стола

# Файл для хранения зарегистрированных столов (опционально)
TABLES_FILE = "tables.json"

def load_tables():
    if os.path.exists(TABLES_FILE):
        with open(TABLES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_tables(tables):
    with open(TABLES_FILE, "w", encoding="utf-8") as f:
        json.dump(tables, f, indent=2, ensure_ascii=False)

# Загружаем список существующих столов (можно не использовать)
tables_db = load_tables()

# Словарь: user_id -> номер стола
user_table = {}

# Клавиатура для гостя (после ввода стола)
guest_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛎️ Позвать официанта")],
        [KeyboardButton(text="💰 Рассчитать счёт")]
    ],
    resize_keyboard=True
)

# Клавиатура с кнопкой "Отмена" (при вводе стола)
cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)

# ========== ОБРАБОТЧИКИ ==========

# Команда /start — просим ввести номер стола
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    logging.info(f"Команда /start от {message.from_user.id}")
    
    # Сбрасываем предыдущее состояние (если было)
    await state.clear()
    
    # Переходим в состояние ожидания номера стола
    await state.set_state(TableState.waiting_for_table)
    
    await message.answer(
        "🍽️ **Добро пожаловать в наше кафе!**\n\n"
        "Пожалуйста, **введите номер вашего стола** цифрами.\n\n"
        "Например: `12`",
        parse_mode="Markdown",
        reply_markup=cancel_kb
    )

# Обработка ввода номера стола
@dp.message(TableState.waiting_for_table)
async def process_table_number(message: types.Message, state: FSMContext):
    # Если пользователь нажал "Отмена"
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Ввод отменён. Если захотите вызвать официанта, отправьте /start",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Проверяем, что введено число
    try:
        table_num = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите **номер стола цифрами**.\n\n"
            "Например: `15`",
            parse_mode="Markdown"
        )
        return
    
    # Проверяем, что номер стола в разумных пределах
    if table_num < 1 or table_num > 100:
        await message.answer(
            "❌ Номер стола должен быть от 1 до 100.\n"
            "Пожалуйста, введите корректный номер."
        )
        return
    
    # Сохраняем номер стола
    user_table[message.from_user.id] = table_num
    
    # Выходим из состояния
    await state.clear()
    
    # Показываем основное меню
    await message.answer(
        f"🍽️ **Стол №{table_num}**\n\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=guest_kb
    )

# Кнопка "Позвать официанта"
@dp.message(lambda msg: msg.text == "🛎️ Позвать официанта")
async def call_waiter(message: types.Message):
    logging.info(f"Вызов официанта от {message.from_user.id}")
    
    table = user_table.get(message.from_user.id)
    if not table:
        await message.answer(
            "❌ Стол не определён.\n"
            "Пожалуйста, отправьте команду /start и укажите номер стола."
        )
        return
    
    # Отправляем уведомление в группу
    try:
        username = f"@{message.from_user.username}" if message.from_user.username else "без юзернейма"
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"🛎️ **ВЫЗОВ ОФИЦИАНТА**\n\n"
            f"• Стол №{table}\n"
            f"• Гость: {username}"
        )
        await message.answer(
            f"✅ Официант уже уведомлён о вызове со стола №{table}!\n"
            f"Пожалуйста, подождите минуту."
        )
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")
        await message.answer("⚠️ Не удалось уведомить официанта. Пожалуйста, позовите голосом.")

# Кнопка "Рассчитать счёт"
@dp.message(lambda msg: msg.text == "💰 Рассчитать счёт")
async def ask_bill(message: types.Message):
    logging.info(f"Запрос счёта от {message.from_user.id}")
    
    table = user_table.get(message.from_user.id)
    if not table:
        await message.answer(
            "❌ Стол не определён.\n"
            "Пожалуйста, отправьте команду /start и укажите номер стола."
        )
        return
    
    # Отправляем запрос в группу
    try:
        username = f"@{message.from_user.username}" if message.from_user.username else "без юзернейма"
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"💰 **ЗАПРОС СЧЁТА**\n\n"
            f"• Стол №{table}\n"
            f"• Гость: {username}"
        )
        await message.answer(
            f"✅ Официант принесёт счёт на стол №{table} через минуту."
        )
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")
        await message.answer("⚠️ Не удалось передать запрос. Пожалуйста, позовите официанта.")

# Команда /reset — сбросить стол (если гость ошибся)
@dp.message(Command("reset"))
async def reset_table(message: types.Message, state: FSMContext):
    if message.from_user.id in user_table:
        del user_table[message.from_user.id]
    await state.clear()
    await message.answer(
        "🔄 Стол сброшен. Чтобы начать заново, отправьте /start",
        reply_markup=ReplyKeyboardRemove()
    )

# Команда /help — справка
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 **Как пользоваться ботом:**\n\n"
        "1. Отправьте команду `/start`\n"
        "2. Введите номер вашего стола (например, `12`)\n"
        "3. Выберите нужное действие:\n"
        "   • 🛎️ Позвать официанта\n"
        "   • 💰 Рассчитать счёт\n\n"
        "Если ошиблись столом — отправьте `/reset` и затем `/start` заново."
    )

# Обработчик неизвестных сообщений
@dp.message()
async def unknown_message(message: types.Message):
    await message.answer(
        "❌ Неизвестная команда.\n"
        "Отправьте /help для списка команд"
    )

# ========== ЗАПУСК БОТА ==========
async def main():
    print("=" * 40)
    print("🚀 ЗАПУСК БОТА (упрощённая версия)")
    print("=" * 40)
    
    await bot.delete_webhook(drop_pending_updates=True)
    
    me = await bot.get_me()
    print(f"✅ Бот: @{me.username}")
    print(f"✅ Группа для уведомлений: {ADMIN_CHAT_ID}")
    print("=" * 40)
    print("🎯 Бот готов к работе!")
    print("📱 Гость: /start → вводит номер стола → выбирает действие")
    print("=" * 40)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
