import asyncio
import logging
import random
import os
import sqlite3
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from dotenv import load_dotenv

# Завантаження змінних середовища
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

if not TOKEN:
    raise ValueError("❌ Токен не знайдено! Перевірте файл .env.")
if not PIXABAY_API_KEY:
    raise ValueError("❌ API-ключ Pixabay не знайдено! Перевірте файл .env.")

# Налаштування логування
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Ініціалізація бота і диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Часовий пояс Києва
kyiv_tz = timezone("Europe/Kyiv")

# Список Telegram user_id для отримання повідомлень від бота
ADMIN_USER_IDS = [471637263, 5142786008]  # Замініть на список реальних user_id

# Підключення до бази даних
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Створення таблиці користувачів
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    username TEXT,
                    first_name TEXT
                )''')
conn.commit()

# Функція для створення клавіатури з кнопками
def create_reaction_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️", callback_data="reaction:like"),
            InlineKeyboardButton(text="🔄", callback_data="reaction:new_photo"),
        ]
    ])
    return keyboard

# Функція для додавання користувача до бази даних
def add_user(user_id, username, first_name):
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    ''', (user_id, username, first_name))
    conn.commit()
    # Надсилаємо адміністраторам повідомлення про додавання користувача
    for admin_id in ADMIN_USER_IDS:
        asyncio.create_task(bot.send_message(
            admin_id,
            f"✅ Новий користувач доданий:\nID: {user_id}\nІм'я: {first_name}\nНікнейм: @{username if username else 'немає'}"
        ))

# Функція для видалення користувача з бази даних
def remove_user(user_id):
    cursor.execute('SELECT username, first_name FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    # Надсилаємо адміністраторам повідомлення про видалення користувача
    if user:
        username, first_name = user
        for admin_id in ADMIN_USER_IDS:
            asyncio.create_task(bot.send_message(
                admin_id,
                f"❌ Користувач видалений:\nID: {user_id}\nІм'я: {first_name}\nНікнейм: @{username if username else 'немає'}"
            ))

# Функція для отримання всіх користувачів з бази даних
def get_all_users():
    cursor.execute('SELECT user_id, username, first_name FROM users')
    return cursor.fetchall()

# Функція для отримання випадкового зображення за темою
def get_random_image(query="funny, kids, sunset, motivation, mountains, forests, cute"):
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&per_page=50"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data["hits"]:
            return random.choice(data["hits"])["webformatURL"]
    return None

# Обробник команди /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    add_user(user_id, username, first_name)
    await message.answer(f"Привіт, {first_name}! Ти додана у список розсилки.")
    logging.info(f"✅ Користувач {user_id} ({username}) доданий у список розсилки.")

# Обробник команди /sendnow для миттєвої розсилки
@dp.message(Command("sendnow"))
async def send_now_handler(message: types.Message):
    if message.from_user.id in ADMIN_USER_IDS:  # Перевіряємо, чи це адміністратор
        await send_random_messages()
    else:
        await message.answer("❌ У вас немає прав для виконання цієї команди.")

# Обробник команди /get_users для отримання списку учасників
@dp.message(Command("get_users"))
async def get_users_handler(message: types.Message):
    if message.from_user.id in ADMIN_USER_IDS:  # Перевіряємо, чи це адміністратор
        users = get_all_users()
        if users:
            user_list = "\n".join([f"ID: {user[0]}, Ім'я: {user[2]}, Нікнейм: @{user[1] if user[1] else 'немає'}" for user in users])
            await message.answer(f"📋 Список учасників:\n{user_list}")
        else:
            await message.answer("❌ Список учасників порожній.")
    else:
        await message.answer("❌ У вас немає прав для виконання цієї команди.")

# Обробник команди /add_user для ручного додавання користувача
@dp.message(Command("add_user"))
async def add_user_handler(message: types.Message):
    if message.from_user.id in ADMIN_USER_IDS:  # Перевіряємо, чи це адміністратор
        try:
            # Розділяємо текст команди на параметри
            command_parts = message.text.split(maxsplit=3)
            if len(command_parts) < 4:
                await message.answer("❌ Неправильний формат. Використовуйте: /add_user <user_id> <username> <first_name>")
                return

            user_id = int(command_parts[1])
            username = command_parts[2]
            first_name = command_parts[3]

            # Додаємо користувача до бази даних
            add_user(user_id, username, first_name)
            await message.answer(f"✅ Користувач доданий:\nID: {user_id}\nІм'я: {first_name}\nНікнейм: @{username}")
        except ValueError:
            await message.answer("❌ Неправильний формат. user_id має бути числом.")
        except Exception as e:
            await message.answer(f"❌ Помилка при додаванні користувача: {e}")
    else:
        await message.answer("❌ У вас немає прав для виконання цієї команди.")

# Функція для розсилки випадкових приємних повідомлень
async def send_random_messages():
    messages = [
        "Ти чудовий!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особливий!", "Ти чудовий!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особливий!",
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
        "Розправ крила і лети до своєї мрії!", "Ти можеш досягти всього, що задумано!", "Новий день – нові можливості. Вперед!",      "Ти неймовірний!", "Вір у себе – ти здатний на більше!", "Ти здолаєш будь-які труднощі!",
        "Ніколи не здавайся!", "Кожен день – це новий шанс!", "У тебе є все, щоб досягти мети!",
        "Продовжуй рухатися вперед, ти на правильному шляху!", "Твоя рішучість – твій ключ до успіху!",
        "Життя дарує тобі безліч можливостей, скористайся ними!", "Не бійтеся мріяти – мрії здійснюються!",
        "Ти сильний, навіть коли не відчуваєш це!", "Ти здатний подолати будь-які перешкоди!",
        "У тебе є все, щоб досягти великих висот!", "Вір у свої сили, і все буде добре!",
        "Завжди пам'ятай, що ти вартий більше!", "Продовжуй розвиватися – кожен крок вперед важливий!",
        "Ти вже на шляху до великої мети!", "Немає нічого неможливого для того, хто вірить!",
        "Кожен день – це шанс стати кращим!", "Твоя стійкість захоплює!",
        "У тебе є все, щоб змінити своє життя на краще!", "Сьогоднішній день – це новий початок!",
        "Ти не один – ми всі тут, щоб підтримати тебе!", "Не бійтеся бути іншими, ви вже унікальні!",
        "Всі великі досягнення починаються з маленьких кроків!", "Ти – приклад для наслідування!",
        "Ваша рішучість і сила волі неймовірні!", "Пам’ятай, що ти – невід’ємна частина цього світу!",
        "Ти вже зробив перший крок, тепер іди далі!", "Підкорюй свої мрії та амбіції!",
        "Сміливо йди вперед, світ чекає на тебе!", "Ти все здолаєш!",
        "У тебе є сила зробити цей день особливим!", "Що б не сталося, пам’ятай: ти завжди маєш можливість змінити ситуацію!",
        "Твоя енергія не має меж!", "Завжди пам’ятай про свою цінність!",
        "Ти маєш силу змінювати світ на краще!", "Ти справжній герой у власній історії!",
        "Сьогодні буде ще один чудовий день!", "Твоя рішучість допоможе тобі подолати будь-які труднощі!",
        "Ти маєш внутрішню силу, яка допоможе подолати все!", "Ти заслуговуєш на всі найкращі речі в житті!",
        "Ти – натхнення для багатьох!", "Не бійтеся змін, вони приводять до великого!",
        "Ваша ціль зовсім близько, тримайся!", "Ти сильніший, ніж ти думаєш!",
        "Будь впевнений у собі – ти справжній лідер!", "У тебе є все для того, щоб створити своє щастя!",
        "Ти – унікальний, не забувай про це!", "Життя не має меж, і твої можливості – теж!",
        "Сьогодні саме той день, щоб розпочати новий шлях!", "Ти – чудовий, продовжуй працювати над собою!",
        "Вір у себе, і ти побачиш чудеса!", "Твоя праця обов'язково принесе плоди!",
        "Не забувай, що ти сильніший за будь-які обставини!", "Ваша енергія може змінити цей світ!",
        "Ти вже на півшляху до своєї мети!", "У тебе є все для того, щоб бути щасливим!",
        "Ти народжений для великих справ!", "Кожен крок наближає тебе до мрії!",
        "Твоя рішучість і віра в себе безцінні!", "Ти справжній боєць – продовжуй боротися!",
        "Всі великі досягнення починаються з маленьких кроків!", "Ти здатний на більше, ніж ти думаєш!",
        "Не бійтеся труднощів – вони роблять вас сильнішими!", "Не забувай, що ти здатний змінити світ!",
        "Ти вже зробив найважчий крок – дій!", "Ти можеш зробити все, що забажаєш!",
        "Твоя віра в себе – це твоя сила!", "Будь відважним, мрії здійснюються!",
        "Ти здатний досягти будь-якої вершини!", "Не дозволяй сумнівам зупиняти тебе!",
        "Кожен день – це шанс стати кращим!", "Ти володієш безмежною енергією!",
        "У тебе є все для того, щоб здійснити свої мрії!", "Ти здатний підкорити будь-які вершини!",
        "Твоя рішучість допоможе тобі подолати всі труднощі!", "Ти готовий до нових звершень!",
        "Ти чудовий, і це не можна заперечити!", "Вір у себе і не бійтеся помилок!",
        "Ти – джерело позитиву для навколишніх!", "Справжня сила в твоїх руках!",
        "Пам’ятай, що немає нічого неможливого!", "Ти заслуговуєш на найкраще!",
        "Твій шлях – це шлях перемоги!", "Будь сміливим, ти здатний на великі справи!",
        "Ти вже близько до своєї мети – продовжуй йти!", "Не бійтеся виглядати іншими – це ваш стиль!",
        "Кожен день приносить нові можливості!", "Ти – переможець у будь-якій ситуації!",
        "Твоя енергія – це твоє величезне багатство!", "Ти здатний змінити своє життя!",
        "Вір у себе, і весь світ відкриється для тебе!", "Ти – справжній майстер своєї долі!",
        "Рухайся вперед, ти вже зробив перший крок!", "Ти готовий до великих досягнень!",
        "Ти здатний бути кращим версією себе!", "Ти маєш неймовірний потенціал!",
        "Твоя рішучість вражає!", "Ти надихаєш інших своєю силою волі!"
    ]

    for user_id, username, first_name in get_all_users():
        try:
            message = random.choice(messages)
            image = get_random_image(query="motivation")  # Задайте тему, наприклад, "motivation"
            if image:
                await bot.send_photo(
                    user_id,
                    photo=image,
                    caption=message,
                    reply_markup=create_reaction_keyboard()  # Додаємо клавіатуру
                )
                logging.info(f"📨 Повідомлення з картинкою надіслано {user_id}")
            else:
                logging.warning("⚠️ Не вдалося отримати зображення з Pixabay.")
        except Exception as e:
            logging.warning(f"⚠️ Не вдалося надіслати {user_id}: {e}")

# Обробник команди /t для розсилки повідомлення всім користувачам
@dp.message(Command("t"))
async def broadcast_handler(message: types.Message):
    if message.from_user.id in ADMIN_USER_IDS:  # Перевіряємо, чи це адміністратор
        try:
            # Отримуємо текст повідомлення або підпис до фото
            if message.caption:  # Якщо є підпис до фото
                broadcast_message = " ".join(message.caption.split()[1:])
            elif message.text:  # Якщо є текст після команди
                broadcast_message = " ".join(message.text.split()[1:])
            else:  # Якщо немає тексту або підпису
                broadcast_message = None

            users = get_all_users()  # Отримуємо список усіх користувачів

            if not users:
                await message.answer("❌ Немає користувачів для розсилки.")
                return

            # Розсилаємо повідомлення кожному користувачу, крім адміністратора, який його відправив
            for user_id, username, first_name in users:
                if user_id == message.from_user.id:  # Пропускаємо адміністратора, який відправив повідомлення
                    continue
                try:
                    if message.photo:  # Якщо є фото
                        await bot.send_photo(user_id, photo=message.photo[-1].file_id, caption=broadcast_message)
                    elif broadcast_message:  # Якщо тільки текст
                        await bot.send_message(user_id, broadcast_message)
                    logging.info(f"📨 Повідомлення надіслано користувачу {user_id}")
                except Exception as e:
                    logging.warning(f"⚠️ Не вдалося надіслати повідомлення користувачу {user_id}: {e}")

            await message.answer("✅ Повідомлення успішно розіслано всім користувачам, крім вас!")
        except IndexError:
            await message.answer("❌ Неправильний формат. Використовуйте: /t <текст повідомлення> або прикріпіть фото з підписом.")
        except Exception as e:
            await message.answer(f"❌ Помилка при розсилці: {e}")
    else:
        await message.answer("❌ У вас немає прав для виконання цієї команди.")

# Обробник натискань на кнопки
@dp.callback_query()
async def handle_reaction(callback_query: types.CallbackQuery):
    data = callback_query.data  # Отримуємо callback_data
    user_id = callback_query.from_user.id

    if data == "reaction:like":
        await callback_query.answer("❤️ Дякую за сердечко!")
        logging.info(f"Користувач {user_id} натиснув 'Сердечко'.")
    elif data == "reaction:new_photo":
        # Відправляємо нове фото
        new_image = get_random_image(query="motivation")
        if new_image:
            await bot.send_photo(
                user_id,
                photo=new_image,
                caption="Ось нове фото для тебе!",
                reply_markup=create_reaction_keyboard()
            )
        await callback_query.answer("🔄 Ось нове фото!")
        logging.info(f"Користувач {user_id} запросив нове фото.")

# Планувальник для щоденних повідомлень (2 рази на день)
scheduler = AsyncIOScheduler()
scheduler.add_job(send_random_messages, CronTrigger(hour=18, minute=0, timezone=kyiv_tz))  # 18:00

# Основна функція запуску бота
async def main():
    scheduler.start()  # Запускаємо планувальник
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
