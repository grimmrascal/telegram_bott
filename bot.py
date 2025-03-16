import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger  # Використовуємо CronTrigger замість DailyTrigger
import random

# Завантажуємо змінні середовища локально (для розробки) або використовуємо їх безпосередньо на Railway
load_dotenv()  # автоматично шукає файл .env в кореневій директорії

# Отримуємо токен бота з змінних середовища
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ Токен не знайдено! Перевірте файл .env або налаштуйте змінні середовища на Railway.")

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота і диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Список користувачів, які почали взаємодію з ботом
active_users = set()

# Обробник команди /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    active_users.add(user_id)
    await message.answer(f"Привіт, {message.from_user.first_name}! Я твій Telegram бот.")

# Обробник команди /sendnow
@dp.message(Command("sendnow"))
async def send_now_handler(message: types.Message):
    # Надсилаємо повідомлення всім користувачам
    messages = [
        "Ти чудовий!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особливий!"
    ]
    for user_id in active_users:
        try:
            await bot.send_message(user_id, random.choice(messages))
        except Exception as e:
            logging.warning(f"Не вдалося надіслати повідомлення {user_id}: {e}")
    await message.answer("Повідомлення надіслано всім активним користувачам!")

# Функція для відправки повідомлення о 10 ранку кожного дня
async def send_daily_message():
    messages = [
        "Доброго ранку! Ти чудовий!", 
        "Не забувай посміхатися сьогодні!", 
        "В тебе все вийде цього дня!", 
        "Ти особливий! Пам'ятай про це!"
    ]
    for user_id in list(active_users):
        try:
            await bot.send_message(user_id, random.choice(messages))
        except Exception as e:
            logging.warning(f"Не вдалося надіслати повідомлення {user_id}: {e}")

# Функція для планування відправки повідомлень о 10 ранку кожного дня
async def schedule_daily_message():
    scheduler = AsyncIOScheduler()
    trigger = CronTrigger(hour=13, minute=0)  # 10 ранку кожного дня
    scheduler.add_job(send_daily_message, trigger)
    scheduler.start()

# Основна функція запуску бота
async def main():
    # Плануємо надсилання щоденних повідомлень о 10 ранку
    asyncio.create_task(schedule_daily_message())

    # Запускаємо безперервне опитування для обробки повідомлень
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
