import asyncio
import logging
import random
import os
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from dotenv import load_dotenv

# Завантаження змінних середовища
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN or not DATABASE_URL:
    raise ValueError("❌ Токен або URL бази даних не знайдено! Перевірте файл .env.")

# Налаштування логування
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Ініціалізація бота і диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Часовий пояс Києва
kyiv_tz = timezone("Europe/Kyiv")

# Підключення до бази даних
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY
        )
    """)
    await conn.close()

# Додавання користувача в базу
async def add_user(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)
    await conn.close()

# Видалення користувача з бази
async def remove_user(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
    await conn.close()

# Отримання всіх користувачів з бази
async def get_all_users():
    conn = await asyncpg.connect(DATABASE_URL)
    users = await conn.fetch("SELECT user_id FROM users")
    await conn.close()
    return [user["user_id"] for user in users]

# Обробник команди /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    await add_user(user_id)
    await message.answer(f"Привіт, {message.from_user.first_name}! Ти доданий у список розсилки.")
    logging.info(f"✅ Користувач {user_id} доданий у базу.")

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
    users = await get_all_users()
    for user_id in users:
        try:
            await bot.send_message(user_id, random.choice(messages))
            logging.info(f"📨 Повідомлення надіслано {user_id}")
        except Exception as e:
            logging.warning(f"⚠️ Не вдалося надіслати {user_id}: {e}")

# Логування всіх оновлень (для діагностики)
@dp.update()
async def all_updates_handler(update: types.Update):
    logging.info(f"📥 Отримано оновлення: {update}")

# Обробник виходу користувача з чату
@dp.chat_member()
async def chat_member_handler(update: types.ChatMemberUpdated):
    user_id = update.from_user.id
    new_status = update.new_chat_member.status

    if new_status in ["kicked", "left"]:
        await remove_user(user_id)
        logging.info(f"❌ Користувач {user_id} видалений з бази.")

# Планувальник для щоденних повідомлень (2 рази на день)
scheduler = AsyncIOScheduler()
scheduler.add_job(send_random_messages, CronTrigger(hour=10, minute=0, timezone=kyiv_tz))  # 10:00
scheduler.add_job(send_random_messages, CronTrigger(hour=18, minute=0, timezone=kyiv_tz))  # 18:00

# Основна функція запуску бота
async def main():
    await init_db()  # Ініціалізуємо БД
    scheduler.start()  # Запускаємо планувальник
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())