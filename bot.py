import asyncio
import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from dotenv import load_dotenv

# Завантаження змінних середовища
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ Токен не знайдено! Перевірте файл .env.")

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота і диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Список активних користувачів
active_users = set()

# Часовий пояс Києва
kyiv_tz = timezone("Europe/Kyiv")

# Обробник команди /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    active_users.add(user_id)
    await message.answer(f"Привіт, {message.from_user.first_name}! Я твій Telegram бот.")

# Обробник команди /sendnow для миттєвої розсилки
@dp.message(Command("sendnow"))
async def send_now_handler(message: types.Message):
    await send_random_messages()
    await message.answer("✅ Повідомлення надіслано всім активним користувачам!")

# Функція для розсилки випадкових приємних повідомлень
async def send_random_messages():
    messages = [
        "Ти чудовий!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особливий!"
    ]
    for user_id in list(active_users):
        try:
            await bot.send_message(user_id, random.choice(messages))
        except Exception as e:
            logging.warning(f"Не вдалося надіслати повідомлення {user_id}: {e}")

# Планувальник для щоденних повідомлень
scheduler = AsyncIOScheduler()

# Запланувати розсилку о 10:00 за Києвом
scheduler.add_job(send_random_messages, CronTrigger(hour=15, minute=9, timezone=kyiv_tz))

# Основна функція запуску бота
async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
