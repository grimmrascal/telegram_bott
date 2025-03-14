import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.filters import Command
import schedule
import time

TOKEN = "redboom_bot"  # Встав сюди свій токен
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Список користувачів, які отримуватимуть розсилку
subscribers = set()

# Список випадкових повідомлень
random_messages = [
    "Привіт! Як справи?",
    "Не забувай посміхатися сьогодні 😊",
    "Ти молодець! Продовжуй у тому ж дусі!",
    "Час випити кави ☕️",
    "Новий день – нові можливості!",
    "Цікаво, що хорошого сталося у тебе сьогодні?"
]

@dp.message(Command("start"))
async def start(message: types.Message):
    subscribers.add(message.chat.id)
    await message.answer("Ви підписані на рандомну розсилку!")

@dp.message(Command("stop"))
async def stop(message: types.Message):
    subscribers.discard(message.chat.id)
    await message.answer("Ви відписалися від розсилки.")

async def send_random_message():
    """Надсилає випадкове повідомлення кожному підписнику"""
    if not subscribers:
        return
    message_text = random.choice(random_messages)
    for user_id in subscribers:
        try:
            await bot.send_message(user_id, message_text)
        except Exception as e:
            logging.error(f"Помилка надсилання до {user_id}: {e}")

def schedule_task():
    """Фоновий процес для запуску розкладу"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        schedule.run_pending()
        time.sleep(10)

@dp.message(Command("send_now"))
async def send_now(message: types.Message):
    """Миттєва розсилка"""
    await send_random_message()
    await message.answer("Рандомна розсилка запущена вручну!")

async def main():
    # Розсилка щодня о 10:00 та 18:00
    schedule.every().day.at("10:00").do(lambda: asyncio.create_task(send_random_message()))
    schedule.every().day.at("18:00").do(lambda: asyncio.create_task(send_random_message()))

    loop = asyncio.get_running_loop()
    loop.create_task(schedule_task())

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
