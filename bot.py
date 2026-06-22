import asyncio
import logging
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

logging.basicConfig(level=logging.INFO)

# ========== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
# =========================================

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан")
if not ADMIN_CHAT_ID:
    raise ValueError("ADMIN_CHAT_ID не задан")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище данных пользователей
user_tables = {}      # user_id -> номер стола
waiting_for_table = {} # user_id -> ожидание ввода стола

# ========== КЛАВИАТУРА С ТРЕМЯ КНОПКАМИ ==========
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛎️ Позвать официанта")],
        [KeyboardButton(text="💰 Рассчитать счёт")],
        [KeyboardButton(text="💨 Вызвать кальянщика")]
    ],
    resize_keyboard=True
)

# ========== ФУНКЦИЯ ОЧИСТКИ В 03:00 ==========
async def daily_cleanup():
    """Очищает все данные пользователей каждый день в 03:00 по Москве"""
    while True:
        now = datetime.now()
        next_cleanup = now.replace(hour=3, minute=0, second=0, microsecond=0)
        
        if now >= next_cleanup:
            next_cleanup += timedelta(days=1)
        
        seconds_to_wait = (next_cleanup - now).total_seconds()
        
        hours = int(seconds_to_wait // 3600)
        minutes = int((seconds_to_wait % 3600) // 60)
        logging.info(f"⏰ Следующая очистка данных через {hours} ч {minutes} мин (в 03:00 по Москве)")
        
        await asyncio.sleep(seconds_to_wait)
        
        user_tables.clear()
        waiting_for_table.clear()
        
        logging.info("🧹 Очистка данных пользователей выполнена в 03:00 {}".format(datetime.now()))
        
        try:
            await bot.send_message(ADMIN_CHAT_ID, "🧹 Данные пользователей очищены (03:00 по Москве)")
        except:
            pass

# ========== ОБРАБОТЧИКИ ==========

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in user_tables:
        old_table = user_tables[user_id]
        await message.answer(
            f"🍽️ У вас уже выбран стол №{old_table}\n\n"
            f"Хотите использовать его или ввести новый?\n\n"
            f"• Введите номер стола для смены\n"
            f"• Или нажмите кнопку ниже",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔄 Оставить текущий стол")]],
                resize_keyboard=True
            )
        )
        waiting_for_table[user_id] = True
        return
    
    waiting_for_table[user_id] = True
    await message.answer(
        "🍽️ Добро пожаловать!\n\nВведите номер вашего стола:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
    )

@dp.message(lambda msg: msg.text == "🔄 Оставить текущий стол")
async def keep_table(message: types.Message):
    user_id = message.from_user.id
    table = user_tables.get(user_id)
    if table:
        waiting_for_table.pop(user_id, None)
        await message.answer(
            f"🍽️ Стол №{table}\n\nВыберите действие:",
            reply_markup=main_kb
        )
    else:
        await message.answer("Ошибка. Отправьте /start заново.")

@dp.message(lambda msg: msg.text == "❌ Отмена")
async def cancel(message: types.Message):
    waiting_for_table.pop(message.from_user.id, None)
    user_tables.pop(message.from_user.id, None)
    await message.answer("Отменено. Отправьте /start", reply_markup=ReplyKeyboardRemove())

@dp.message(lambda msg: waiting_for_table.get(msg.from_user.id, False))
async def get_table(message: types.Message):
    try:
        table_num = int(message.text)
        if table_num < 1 or table_num > 100:
            await message.answer("Номер стола от 1 до 100. Попробуйте ещё раз:")
            return
        user_tables[message.from_user.id] = table_num
        waiting_for_table.pop(message.from_user.id, None)
        await message.answer(
            f"🍽️ Стол №{table_num}\n\nВыберите действие:",
            reply_markup=main_kb
        )
    except ValueError:
        await message.answer("Введите номер стола цифрами.")

# ========== КНОПКА ВЫЗОВА ОФИЦИАНТА ==========
@dp.message(lambda msg: msg.text == "🛎️ Позвать официанта")
async def call_waiter(message: types.Message):
    table = user_tables.get(message.from_user.id)
    if not table:
        await message.answer("Сначала отправьте /start и укажите номер стола.")
        return
    
    username = f"@{message.from_user.username}" if message.from_user.username else "гость"
    try:
        await bot.send_message(ADMIN_CHAT_ID, f"🛎️ ВЫЗОВ ОФИЦИАНТА — Стол {table} ({username})")
        await message.answer(f"✅ Официант уведомлён о вызове со стола {table}!")
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")
        await message.answer("❌ Ошибка: не удалось отправить уведомление. Сообщите официанту лично.")

# ========== КНОПКА РАССЧИТАТЬ СЧЁТ ==========
@dp.message(lambda msg: msg.text == "💰 Рассчитать счёт")
async def ask_bill(message: types.Message):
    table = user_tables.get(message.from_user.id)
    if not table:
        await message.answer("Сначала отправьте /start и укажите номер стола.")
        return
    
    username = f"@{message.from_user.username}" if message.from_user.username else "гость"
    try:
        await bot.send_message(ADMIN_CHAT_ID, f"💰 ЗАПРОС СЧЁТА — Стол {table} ({username})")
        await message.answer(f"✅ Счёт принесут на стол {table}!")
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")
        await message.answer("❌ Ошибка: не удалось отправить запрос. Сообщите официанту лично.")

# ========== КНОПКА ВЫЗОВА КАЛЬЯНЩИКА ==========
@dp.message(lambda msg: msg.text == "💨 Вызвать кальянщика")
async def call_hookah(message: types.Message):
    table = user_tables.get(message.from_user.id)
    if not table:
        await message.answer("Сначала отправьте /start и укажите номер стола.")
        return
    
    username = f"@{message.from_user.username}" if message.from_user.username else "гость"
    try:
        await bot.send_message(ADMIN_CHAT_ID, f"💨 ВЫЗОВ КАЛЬЯНЩИКА — Стол {table} ({username})")
        await message.answer(f"✅ Кальянщик уведомлён о вызове со стола {table}!")
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")
        await message.answer("❌ Ошибка: не удалось отправить уведомление. Сообщите кальянщику лично.")

# ========== ОСТАЛЬНЫЕ КОМАНДЫ ==========
@dp.message(Command("reset"))
async def reset(message: types.Message):
    user_tables.pop(message.from_user.id, None)
    waiting_for_table.pop(message.from_user.id, None)
    await message.answer("Стол сброшен. Отправьте /start.", reply_markup=ReplyKeyboardRemove())

@dp.message(Command("getid"))
async def get_id(message: types.Message):
    await message.answer(f"ID этого чата: `{message.chat.id}`", parse_mode="Markdown")

# ========== ЗАПУСК БОТА ==========
async def main():
    print("🚀 Бот запускается...")
    
    asyncio.create_task(daily_cleanup())
    print("✅ Запланирована ежедневная очистка данных в 03:00 по Москве")
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook очищен")
    
    me = await bot.get_me()
    print(f"✅ Бот @{me.username} готов к работе!")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
