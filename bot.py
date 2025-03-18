import os
import random
import asyncio
import logging
import requests
import psycopg2
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.markdown import hbold
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
from datetime import datetime
from dotenv import load_dotenv

# Завантажуємо змінні середовища
load_dotenv()

# Налаштування
TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
PHOTO_CATEGORIES = ["cute animals", "beautiful landscapes"]  # Теми для фото

# Логування
logging.basicConfig(level=logging.INFO)

# Telegram бот
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Часовий пояс
kyiv_tz = timezone("Europe/Zaporozhye")

# Підключення до бази даних
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# Створення таблиці
def create_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE,
            first_name TEXT,
            username TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# Додавання користувача
async def add_user(user_id, first_name, username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, first_name, username) 
        VALUES (%s, %s, %s) 
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id, first_name, username))
    conn.commit()
    cur.close()
    conn.close()

# Отримання всіх користувачів
def get_all_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    users = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return users

# Отримання рандомного повідомлення
def get_random_message():
    messages = [
        "Гарного дня!",
        "Не забувайте усміхатись! 😊",
        "Нехай удача буде на вашому боці!",
        "Цінуйте кожен момент ❤️"
    ]
    return random.choice(messages)

# Отримання випадкового фото з Pixabay
def get_random_photo():
    category = random.choice(PHOTO_CATEGORIES)
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={category}&image_type=photo&per_page=50"
    response = requests.get(url).json()
    if "hits" in response and response["hits"]:
        return random.choice(response["hits"])["webformatURL"]
    return None

# Розсилка рандомних повідомлень та фото
async def send_random_messages():
    users = get_all_users()
    for user_id in users:
        message = get_random_message()
        photo_url = get_random_photo()
        if photo_url:
            await bot.send_photo(user_id, photo_url, caption=message)
        else:
            await bot.send_message(user_id, message)

# Обробник команди /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await add_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    await message.answer(f"Привіт, {hbold(message.from_user.first_name)}! Я буду надсилати тобі цікаві повідомлення та фото.")

# Обробник команди /sendnow
@dp.message(Command("sendnow"))
async def send_now_handler(message: types.Message):
    await send_random_messages()

# Планувальник задач
scheduler = AsyncIOScheduler()
scheduler.add_job(send_random_messages, "cron", hour=18, timezone=kyiv_tz)  # Запланована розсилка о 18:00
scheduler.start()

# Запуск бота
async def main():
    create_table()  # Створення таблиці при старті
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())