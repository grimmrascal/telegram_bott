import os
import logging
import random
import asyncio
import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.utils.markdown import hbold
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Завантаження змінних середовища
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("\u274C Токен не знайдено! Перевірте файл .env.")

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота і диспетчера
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Список користувачів, які почали взаємодію з ботом
active_users = set()

# Обробник команди /start
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    active_users.add(user_id)
    await message.answer(f"Привіт, {hbold(message.from_user.first_name)}! Я твій Telegram бот.")

# Функція для розсилки випадкових приємних повідомлень
async def send_random_messages():
    messages = [
        "Ти чудовий!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особливий!"
    ]
    while True:
        for user_id in list(active_users):
            try:
                await bot.send_message(user_id, random.choice(messages))
            except Exception as e:
                logging.warning(f"Не вдалося надіслати повідомлення {user_id}: {e}")
        await asyncio.sleep(3600)  # Відправляти кожну годину

# Функція для щоденної розсилки повідомлень
def daily_message_job():
    messages = [
        "Ти чудовий!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особливий!"
    ]
    for user_id in list(active_users):
        try:
            message = random.choice(messages)
            asyncio.create_task(bot.send_message(user_id, message))
        except Exception as e:
            logging.warning(f"Не вдалося надіслати повідомлення {user_id}: {e}")

# Налаштування планувальника для щоденної розсилки о 10:00
scheduler = AsyncIOScheduler()
scheduler.add_job(daily_message_job, IntervalTrigger(days=1, start_date=datetime.datetime.now().replace(hour=10, minute=0, second=0), timezone="UTC"))
scheduler.start()

# Основна функція запуску бота
async def main():
    # Розпочати задачу для випадкових повідомлень
    asyncio.create_task(send_random_messages())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
