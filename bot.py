import os
import logging
import asyncio
import random
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

# Завантажуємо змінні середовища
load_dotenv()

# Отримуємо токен бота з змінних середовища
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ Токен не знайдено! Перевірте файл .env або налаштуйте змінні середовища на Railway.")

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота і диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Список активних користувачів
active_users = set()

# Обробник команди /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    active_users.add(user_id)
    await message.answer(f"Привіт, {message.from_user.first_name}! Тепер ти в списку активних користувачів.")

# Обробник команди /sendnow (миттєва розсилка)
@dp.message(Command("sendnow"))
async def send_now_handler(message: types.Message):
    messages = [
        "Ти чудовий!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особливий!"
    ]
    for user_id in active_users:
        try:
            await bot.send_message(user_id, random.choice(messages))
        except Exception as e:
            logging.warning(f"Не вдалося надіслати повідомлення {user_id}: {e}")
    await message.answer("✅ Повідомлення надіслано всім активним користувачам!")

# Щоденна розсилка о 10:00 за Києвом
async def send_daily_message():
    messages = [
        "Доброго ранку! 🌞 Ти чудовий!",
        "Нехай цей день принесе тобі щось хороше!",
        "Ти сильний, у тебе все вийде!",
        "З посмішкою легше рухатися вперед! 😊"
    ]
    for user_id in active_users:
        try:
            await bot.send_message(user_id, random.choice(messages))
        except Exception as e:
            logging.warning(f"Не вдалося надіслати повідомлення {user_id}: {e}")

# Функція для планування щоденних повідомлень
async def schedule_daily_message():
    scheduler = AsyncIOScheduler()
    kyiv_tz = timezone("Europe/Kiev")
    trigger = CronTrigger(hour=10, minute=0, timezone=kyiv_tz)  # 10:00 ранку за Києвом
    scheduler.add_job(send_daily_message, trigger)
    scheduler.start()

# Основна функція запуску бота
async def main():
    asyncio.create_task(schedule_daily_message())  # Запускаємо планувальник
    await dp.start_polling(bot)  # Запускаємо бота

if __name__ == "__main__":
    asyncio.run(main())