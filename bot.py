import random
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from dotenv import load_dotenv
import schedule
import time

# Завантажуємо змінні з файлу .env
load_dotenv()

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("❌ Токен не знайдено! Перевірте файл .env.")

# Ініціалізація бота і диспетчера
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Список для зберігання ID користувачів
user_ids = set()

# Список приємних фраз
greetings = [
    "Привіт! Сподіваюсь, у тебе гарний день!",
    "Як твої справи? Сподіваюся, все чудово!",
    "Бажаю гарного настрою! :)",
    "Привіт, друже! Як ти?",
    "Вітаю! Спільно до успіху!"
]

# Функція для розсилки повідомлень
async def send_random_message():
    if user_ids:  # Якщо є користувачі
        user_id = random.choice(list(user_ids))  # Вибір випадкового ID
        message = random.choice(greetings)  # Вибір випадкової фрази
        try:
            await bot.send_message(user_id, message)  # Надсилання повідомлення
            print(f"Повідомлення надіслано користувачу з ID: {user_id}")
        except Exception as e:
            print(f"Не вдалося надіслати повідомлення користувачу з ID {user_id}: {e}")

# Обробник команди /start
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id  # Отримуємо ID користувача
    if user_id not in user_ids:
        user_ids.add(user_id)  # Додаємо ID в список
        await message.answer("Привіт! Тепер ти можеш отримувати випадкові повідомлення від мене!")
    else:
        await message.answer("Ти вже зареєстрований для отримання повідомлень.")

# Завдання для відправки повідомлень кожні 5 хвилин
def job():
    asyncio.run(send_random_message())

# Запускаємо розсилку кожні 5 хвилин
schedule.every(5).minutes.do(job)

# Функція для запуску планувальника
async def scheduler():
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(scheduler())  # Запускаємо планувальник
    executor.start_polling(dp, skip_updates=True)
