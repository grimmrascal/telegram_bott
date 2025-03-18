import asyncio
import logging
import random
import asyncpg
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
from datetime import datetime

# Конфігурація
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
DATABASE_URL = "postgresql://user:password@host:port/dbname"
PIXABAY_API_KEY = "YOUR_PIXABAY_API_KEY"
PHOTO_CATEGORY = "cute"  # Можеш змінити тему фото
CHAT_ID = "YOUR_CHAT_ID"  # ID групи або користувача

# Логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота та диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Часовий пояс
kyiv_tz = timezone("Europe/Zaporozhye")

# Список рандомних повідомлень
messages = [
    "Гарного дня! 🌞",
    "Не забувай посміхатися! 😊",
    "Сьогодні чудовий день для нових звершень!",
    "Тримайся! Все буде добре!",
    "Нехай удача буде з тобою! 🍀"
]

# --------------- ФУНКЦІЇ ДЛЯ БАЗИ ДАНИХ ---------------

async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE NOT NULL,
            first_name TEXT,
            username TEXT
        );
    """)

    columns = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
    existing_columns = {row['column_name'] for row in columns}

    if 'first_name' not in existing_columns:
        await conn.execute("ALTER TABLE users ADD COLUMN first_name TEXT;")
    if 'username' not in existing_columns:
        await conn.execute("ALTER TABLE users ADD COLUMN username TEXT;")
    
    await conn.close()

async def add_user(user_id, first_name, username):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        INSERT INTO users (user_id, first_name, username)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id) DO UPDATE SET first_name = EXCLUDED.first_name, username = EXCLUDED.username;
    """, user_id, first_name, username)
    await conn.close()

async def get_all_users():
    conn = await asyncpg.connect(DATABASE_URL)
    users = await conn.fetch("SELECT user_id FROM users")
    await conn.close()
    return [user["user_id"] for user in users]

# --------------- ФУНКЦІЇ ДЛЯ РОЗСИЛКИ ---------------

async def get_random_photo():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={PHOTO_CATEGORY}&image_type=photo&per_page=50") as response:
            data = await response.json()
            if "hits" in data and data["hits"]:
                return random.choice(data["hits"])["webformatURL"]
            return None

async def send_random_messages():
    users = await get_all_users()
    random.shuffle(users)  # Щоб кожен отримував різні повідомлення
    
    for i, user_id in enumerate(users):
        text = messages[i % len(messages)]  # Беремо унікальне повідомлення для кожного
        photo_url = await get_random_photo()
        
        if photo_url:
            try:
                await bot.send_photo(user_id, photo_url, caption=text)
            except Exception as e:
                logging.error(f"Помилка відправки {user_id}: {e}")
        else:
            try:
                await bot.send_message(user_id, text)
            except Exception as e:
                logging.error(f"Помилка відправки {user_id}: {e}")

# --------------- ОБРОБНИКИ КОМАНД ---------------

@dp.message(commands=["start"])
async def start_handler(message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    await add_user(user_id, first_name, username)
    await message.answer("Вітаю! Ви підписалися на розсилку!")

@dp.message(commands=["sendnow"])
async def send_now_handler(message: Message):
    await send_random_messages()

# --------------- НАЛАШТУВАННЯ ПЛАНУВАЛЬНИКА ---------------

scheduler = AsyncIOScheduler()

# Додаємо розсилку о 18:00 і 20:00
scheduler.add_job(send_random_messages, "cron", hour=18, minute=0, timezone=kyiv_tz)
scheduler.add_job(send_random_messages, "cron", hour=20, minute=0, timezone=kyiv_tz)

scheduler.start()

# --------------- ЗАПУСК БОТА ---------------

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())