import os
import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

# Завантаження змінних середовища
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ Токен не знайдено! Перевірте файл .env.")

# Ініціалізація бота і диспетчера
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Список користувачів, які почали роботу з ботом
active_users = set()

# Приємні фрази для розсилки
phrases = [
    "🌟 Бажаю тобі чудового дня!",
    "😊 Не забувай усміхатися!",
    "💪 Вір у себе – ти можеш усе!",
    "🌞 Гарного настрою на весь день!",
    "🌺 Ти неймовірний/на, не забувай про це!"
]

# Обробник команди /start
@dp.message(CommandStart())
async def send_welcome(message: Message):
    user_id = message.from_user.id
    active_users.add(user_id)
    await message.answer("Привіт! Я твій бот, що піднімає настрій! 🎉")

# Функція для розсилки повідомлень кожні 6 годин
async def send_random_messages():
    while True:
        if active_users:
            phrase = random.choice(phrases)
            for user_id in active_users:
                try:
                    await bot.send_message(user_id, phrase)
                except Exception as e:
                    print(f"❌ Помилка при відправці повідомлення {user_id}: {e}")
        await asyncio.sleep(21600)  # 6 годин (6 * 60 * 60 секунд)

# Запуск бота
async def main():
    asyncio.create_task(send_random_messages())  # Запускаємо фонову розсилку
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
