import os
import asyncio
import logging
import random
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.client.bot import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.utils.markdown import hbold
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.daily import DailyTrigger

# Виведення поточної директорії
print("Поточна робоча директорія:", os.getcwd())

# Завантаження змінних середовища з файлу .env
load_dotenv()  # Можна використовувати без вказівки шляху, якщо .env в тій самій директорії
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("\u274C Токен не знайдено! Перевірте файл .env.")

# Налаштування властивостей за замовчуванням для бота
default_properties = DefaultBotProperties(parse_mode="HTML")

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота з властивостями за замовчуванням
bot = Bot(token=TOKEN, default=default_properties)

# Ініціалізація диспетчера, передаючи параметр bot через ключове значення
dp = Dispatcher(bot=bot)

# Список користувачів, які почали взаємодію з ботом
active_users = set()

# Ініціалізація планувальника
scheduler = AsyncIOScheduler()

# Обробник команди /start
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    active_users.add(user_id)
    await message.answer(f"Привіт, {hbold(message.from_user.first_name)}! Я твій Telegram бот.")

# Обробник команди /sendnow
@dp.message(Command("sendnow"))
async def send_now(message: types.Message):
    messages = [
        "Ти чудовий!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особливий!"
    ]
    for user_id in list(active_users):
        try:
            await bot.send_message(user_id, random.choice(messages))
        except Exception as e:
            logging.warning(f"Не вдалося надіслати повідомлення {user_id}: {e}")
    await message.answer("Повідомлення надіслано всім активним користувачам.")

# Функція для розсилки випадкових приємних повідомлень о 10 ранку
async def send_daily_message():
    messages = [
        "Ти чудовий!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особливий!"
    ]
    for user_id in list(active_users):
        try:
            await bot.send_message(user_id, random.choice(messages))
        except Exception as e:
            logging.warning(f"Не вдалося надіслати повідомлення {user_id}: {e}")

# Планування розсилки о 10 ранку кожного дня
scheduler.add_job(
    send_daily_message,
    DailyTrigger(hour=10, minute=0, second=0, timezone="Europe/Kiev"),  # Кожного дня о 10:00
)

# Основна функція запуску бота
async def main():
    logging.info("Бот запущений")
    scheduler.start()  # Запуск планувальника
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
