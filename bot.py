import logging
import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from dotenv import load_dotenv
import schedule
import time

# Завантажуємо змінні середовища з файлу .env
load_dotenv()

# Отримуємо токен з середовища
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("❌ Токен не знайдено! Перевірте файл .env.")

# Ініціалізація бота та диспетчера
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

# Визначаємо приємні фрази для розсилки
pleasant_phrases = [
    "Привіт! Бажаю тобі чудового дня! 🌞",
    "Нехай цей день принесе тобі радість і успіхи! 🌟",
    "Ти чудова людина! Спільно з тобою світ стає кращим! 💖",
    "Нехай усі твої мрії здійсняться! ✨",
    "Посміхнись, ти заслуговуєш на найкраще! 😊"
]

# Функція для відправки випадкової фрази
async def send_random_message(user_id):
    random_phrase = random.choice(pleasant_phrases)
    try:
        await bot.send_message(user_id, random_phrase)
    except Exception as e:
        logging.error(f"Не вдалося відправити повідомлення: {e}")

# Функція для планування розсилки
def schedule_message():
    # Наприклад, відправляємо повідомлення кожні 10 хвилин
    schedule.every(10).minutes.do(send_random_message, user_id=USER_ID)

# Ця функція буде відправляти повідомлення певному користувачу
USER_ID = <ID_Користувача>  # Заміни на id користувача, якому хочеш відправляти повідомлення

# Запускаємо планування розсилки
schedule_message()

# Функція для запуску планувальника
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Запускаємо розсилку на окремому потоці
loop = asyncio.get_event_loop()
loop.create_task(run_scheduler())

# Команда старту
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer("Привіт! Я ваш бот, який надсилає приємні повідомлення!")

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
