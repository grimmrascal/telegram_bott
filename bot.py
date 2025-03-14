import os
from aiogram import Bot
from aiogram.enums import ParseMode

# Зчитуємо токен з змінної середовища
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("❌ Токен не знайдено! Перевірте файл .env.")

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
from dotenv import load_dotenv
import os

# Завантажуємо змінні середовища з файлу .env
load_dotenv()

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("❌ Токен не знайдено! Перевірте файл .env.")
