from dotenv import load_dotenv
import os

# Завантажуємо змінні середовища з файлу .env
load_dotenv()

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("❌ Токен не знайдено! Перевірте файл .env.")
