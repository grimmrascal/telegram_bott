import asyncio
import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
import aiohttp
import asyncpg
from dotenv import load_dotenv

load_dotenv()

# Налаштування
TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# Часовий пояс
kyiv_tz = timezone("Europe/Kyiv")

# Підключення до бази даних
async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)

async def close_db():
    await pool.close()

# Ініціалізація БД
async def setup_db():
    async with pool.acquire() as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE
            )"""
        )

# Додавання користувача
async def add_user(user_id):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)

# Отримання списку користувачів
async def get_users():
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users")
        return [row["user_id"] for row in rows]

# Отримання випадкового фото з Pixabay за заданою темою
async def get_random_photo(topic="cute"):
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={topic}&image_type=photo&per_page=50"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if "hits" in data and len(data["hits"]) > 0:
                return random.choice(data["hits"])["webformatURL"]
            return None

# Випадкові повідомлення
messages = [
    "Гарного дня!", "Не забувайте посміхатися!", "Сьогодні чудовий день!", "Ви молодець!"
]

# Відправка запланованих повідомлень
async def send_random_messages(topic="cute"):
    users = await get_users()
    text = random.choice(messages)
    photo_url = await get_random_photo(topic)
    
    for user_id in users:
        try:
            if photo_url:
                await bot.send_photo(chat_id=user_id, photo=photo_url, caption=text)
            else:
                await bot.send_message(chat_id=user_id, text=text)
        except Exception as e:
            logging.error(f"Помилка надсилання {user_id}: {e}")

# Команда старт
@dp.message(Command("start"))
async def start(message: types.Message):
    await add_user(message.from_user.id)
    await message.answer("Ви підписалися на розсилку!")

# Команда для миттєвої розсилки
@dp.message(Command("sendnow"))
async def sendnow(message: types.Message):
    topic = "cute"  # За замовчуванням "cute", але можна обирати інші теми
    await send_random_messages(topic)

# Команда для вибору теми
@dp.message(Command("settheme"))
async def set_theme(message: types.Message):
    theme = message.text.split(" ", 1)[1] if len(message.text.split(" ", 1)) > 1 else ""
    
    if theme:
        await message.answer(f"Тема для фото змінена на: {theme}")
        await send_random_messages(theme)
    else:
        await message.answer("Будь ласка, вкажіть тему після команди. Наприклад: /settheme cute")

# Запуск планувальника
scheduler.add_job(send_random_messages, "cron", hour=9, minute=0, timezone=kyiv_tz)
scheduler.add_job(send_random_messages, "cron", hour=12, minute=0, timezone=kyiv_tz)
scheduler.add_job(send_random_messages, "cron", hour=18, minute=0, timezone=kyiv_tz)

async def main():
    await init_db()
    await setup_db()
    scheduler.start()
    await dp.start_polling(bot)
    await close_db()

if __name__ == "__main__":
    asyncio.run(main())