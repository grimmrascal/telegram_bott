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
    raise ValueError("❌ Перевірте файл .env: відсутній BOT_TOKEN або DATABASE_URL.")

# Налаштування логування
logging.basicConfig(level=logging.INFO)

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
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE
        )
    """)
    await conn.close()

# Функція отримання користувачів із бази
async def get_users():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT user_id FROM users")
    await conn.close()
    return [row["user_id"] for row in rows]

# Функція додавання користувача в базу
async def add_user(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING", user_id)
    await conn.close()

# Обробник команди /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    await add_user(user_id)
    await message.answer(f"Привіт, {message.from_user.first_name}! Тепер ти в списку розсилки ✅")

# Обробник команди /sendnow
@dp.message(Command("sendnow"))
async def send_now_handler(message: types.Message):
    await send_random_messages()
    await message.answer("✅ Повідомлення надіслано всім активним користувачам!")

# Функція для розсилки випадкових повідомлень
async def send_random_messages():
    messages = [
        "Ти чудовий!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особливий!",
        "Новий день – нові можливості! Лови їх!", "Ти сильніший, ніж думаєш. Усе вийде!",
        "Сьогодні твій день – зроби його крутим!", "Прокидайся! У світу для тебе є щось особливе!",
        "Сонце вже світить для тебе – час підкорювати світ!", "Зроби сьогодні те, про що завтра подякуєш собі!",
        "Твоя енергія – твоя суперсила! Використай її!", "Кожен новий ранок – це шанс почати спочатку!",
        "Не бійся труднощів – вони роблять тебе сильнішим!", "Сьогодні ти на крок ближче до своєї мрії!",
        "Дихай глибше, усміхайся ширше – вперед до успіху!", "Світ чекає на твої звершення!",
        "Будь собою – це вже твоя суперсила!", "Кава, заряд позитиву і вперед до перемог!",
        "Щасливий день починається з усмішки!", "Не відкладай щастя – створюй його вже сьогодні!",
        "Роби те, що приносить тобі радість!", "Твої старання обов’язково принесуть плоди!",
        "Маленькі кроки ведуть до великих перемог!", "Зараз – найкращий час, щоб почати діяти!",
        "Навіть найтемніший ранок може стати яскравим!", "Відпусти сумніви – вперед до звершень!",
        "Живи цей день так, щоб увечері сказати: “Я молодець!”", "Ти заслуговуєш на щасливе і насичене життя!",
        "Дивись на світ з оптимізмом – він відповість тобі тим самим!", "Кожна твоя дія – це крок до успіху!",
        "Розправ крила і лети до своєї мрії!"
    ]
    users = await get_users()
    for user_id in users:
        try:
            await bot.send_message(user_id, random.choice(messages))
        except Exception as e:
            logging.warning(f"Не вдалося надіслати повідомлення {user_id}: {e}")

# Планувальник для щоденних повідомлень
scheduler = AsyncIOScheduler()
scheduler.add_job(send_random_messages, CronTrigger(hour=10, minute=0, timezone=kyiv_tz))
scheduler.add_job(send_random_messages, CronTrigger(hour=18, minute=0, timezone=kyiv_tz))

# Основна функція запуску бота
async def main():
    await init_db()  # Ініціалізація бази
    scheduler.start()  # Запуск планувальника
    await dp.start_polling(bot)  # Запуск бота

if __name__ == "__main__":
    asyncio.run(main())
