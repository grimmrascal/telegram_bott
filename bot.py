import asyncio
import logging
import random
import os
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter
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
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота і диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Часовий пояс Києва
kyiv_tz = timezone("Europe/Kyiv")

# Підключення до бази даних
async def init_db():
    return await asyncpg.connect(DATABASE_URL)

# Додавання користувача в базу даних
async def add_user(user_id: int):
    conn = await init_db()
    await conn.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING;", user_id)
    await conn.close()

# Видалення користувача з бази даних
async def remove_user(user_id: int):
    conn = await init_db()
    await conn.execute("DELETE FROM users WHERE user_id = $1;", user_id)
    await conn.close()

# Обробник команди /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    await add_user(user_id)
    await message.answer(f"Привіт, {message.from_user.first_name}! Я твій Telegram бот.")

# Обробник команди /sendnow для миттєвої розсилки
@dp.message(Command("sendnow"))
async def send_now_handler(message: types.Message):
    await send_random_messages()
    await message.answer("✅ Повідомлення надіслано всім активним користувачам!")

# Функція для розсилки випадкових приємних повідомлень
async def send_random_messages():
    conn = await init_db()
    users = await conn.fetch("SELECT user_id FROM users;")
    await conn.close()
    
    messages = [
        "Ти чудовий!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особливий!"
    ]
    for user in users:
        user_id = user["user_id"]
        try:
            await bot.send_message(user_id, random.choice(messages))
        except Exception as e:
            logging.warning(f"Не вдалося надіслати повідомлення {user_id}: {e}")

# Обробник видалення чату користувачем
@dp.chat_member(ChatMemberUpdatedFilter(member_status_changed=True))
async def chat_member_handler(update: ChatMemberUpdated):
    user_id = update.from_user.id
    new_status = update.new_chat_member.status

    if new_status in ["kicked", "left"]:  # Якщо користувач вийшов або видалив чат
        await remove_user(user_id)
        logging.info(f"Користувач {user_id} видалений з бази через вихід з чату")

# Планувальник для щоденних повідомлень
scheduler = AsyncIOScheduler()

# Запланувати розсилку о 10:00 та 18:00 за Києвом
scheduler.add_job(send_random_messages, CronTrigger(hour=10, minute=0, timezone=kyiv_tz))
scheduler.add_job(send_random_messages, CronTrigger(hour=18, minute=0, timezone=kyiv_tz))

# Основна функція запуску бота
async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())