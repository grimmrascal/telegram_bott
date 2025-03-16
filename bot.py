import os
import asyncio
import logging
import random
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.markdown import hbold
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncpg
from pytz import timezone

# Завантажуємо змінні середовища
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN or not DATABASE_URL:
    raise ValueError("❌ Не знайдено токен або URL бази даних! Перевірте .env")

# Логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Налаштування часового поясу Києва
kyiv_tz = timezone("Europe/Kyiv")

# Підключення до бази даних
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY)"""
    )
    await conn.close()

# Додаємо користувача в БД
async def add_user(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)
    await conn.close()

# Отримуємо всіх користувачів із БД
async def get_all_users():
    conn = await asyncpg.connect(DATABASE_URL)
    users = await conn.fetch("SELECT user_id FROM users")
    await conn.close()
    return [user["user_id"] for user in users]

# Команда /start
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    await add_user(user_id)
    await message.answer(f"Привіт, {hbold(message.from_user.first_name)}! Ти підписався на розсилку.")

# Випадкові повідомлення
async def send_random_messages():
    messages = [
        "Ти чудовий!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особливий!"
    ]
    users = await get_all_users()
    for user_id in users:
        try:
            await bot.send_message(user_id, random.choice(messages))
        except Exception as e:
            logging.warning(f"Не вдалося надіслати повідомлення {user_id}: {e}")

# Команда /sendnow (ручна відправка)
@dp.message(Command("sendnow"))
async def send_now(message: types.Message):
    await send_random_messages()
    await message.answer("✅ Повідомлення відправлено всім користувачам!")

# Запуск бота
async def main():
    await init_db()
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_random_messages, CronTrigger(hour=15, minute=20, timezone=kyiv_tz))  # Відправка о 10:00
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())