import asyncio
import logging
import random
import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from dotenv import load_dotenv

# Завантаження змінних середовища
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN:
    raise ValueError("❌ Токен не знайдено! Перевірте файл .env.")
if not PIXABAY_API_KEY:
    raise ValueError("❌ API-ключ Pixabay не знайдено! Перевірте файл .env.")
if not DATABASE_URL:
    raise ValueError("❌ URL бази даних не знайдено! Перевірте файл .env.")

# Налаштування логування
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Ініціалізація бота і диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Ініціалізація Router
router = Router()
dp.include_router(router)

# Часовий пояс Києва
kyiv_tz = timezone("Europe/Kyiv")

# Список Telegram user_id для отримання повідомлень від бота
ADMIN_USER_IDS = [471637263, 646146668]  # Замініть на список реальних user_id

# Підключення до бази даних PostgreSQL
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Створення таблиці користувачів
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        user_id BIGINT UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT
    )
''')
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
    try:
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
        ''', (user_id, username, first_name))
        conn.commit()
        logging.info(f"Користувач {user_id} доданий до бази даних.")
    except Exception as e:
        conn.rollback()  # Скасовуємо транзакцію у разі помилки
        logging.error(f"Помилка при додаванні користувача {user_id}: {e}")

# Функція для видалення користувача з бази даних
def remove_user(user_id):
    try:
        cursor.execute('DELETE FROM users WHERE user_id = %s', (user_id,))
        conn.commit()
        logging.info(f"Користувач {user_id} видалений із бази даних.")
    except Exception as e:
        conn.rollback()  # Скасовуємо транзакцію у разі помилки
        logging.error(f"Помилка при видаленні користувача {user_id}: {e}")

# Функція для отримання всіх користувачів з бази даних
def get_all_users():
    try:
        cursor.execute('SELECT user_id, username, first_name FROM users')
        return cursor.fetchall()
    except Exception as e:
        conn.rollback()  # Скасовуємо транзакцію у разі помилки
        logging.error(f"Помилка при отриманні списку користувачів: {e}")
        return []

# Функція для отримання випадкового зображення за темою
def get_random_image(query="mountains, flowers, love"):
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&per_page=50"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data["hits"]:
            return random.choice(data["hits"])["webformatURL"]
    return None

# Обробник команди /start
@router.message(Command("start"))
async def start_handler(message: Message):  # Використовуємо правильний імпортований клас
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    await message.answer("🔒 Введіть пароль для доступу до бота:")

    @router.message()  # Вкладений хендлер — це погана практика, потрібно винести окремо
    async def password_handler(password_message: Message):
        entered_password = password_message.text
        correct_password = os.getenv("BOT_PASSWORD")  

        if entered_password == correct_password:
            add_user(user_id, username, first_name)

            await password_message.answer(f"✅ Пароль правильний! Привіт, {first_name}! Ти додана у список розсилки.")
            logging.info(f"✅ Користувач {user_id} ({username}) доданий у список розсилки.")

            new_user_text = (
                f"🆕 Новий користувач!\n"
                f"👤 Ім'я: {first_name}\n"
                f"🆔 ID: {user_id}\n"
                f"🔗 @{username if username else 'немає'}"
            )
            for admin_id in ADMIN_USER_IDS:
                try:
                    await password_message.bot.send_message(admin_id, new_user_text)
                except Exception as e:
                    logging.warning(f"⚠️ Не вдалося повідомити адміна {admin_id}: {e}")

        else:
            await password_message.answer("❌ Неправильний пароль. Доступ заборонено.")
            logging.warning(f"❌ Невдала спроба доступу користувача {user_id} ({username}).")

# Обробник команди /sendnow для миттєвої розсилки
@dp.message(Command("sendnow"))
async def send_now_handler(message: types.Message):
    if message.from_user.id in ADMIN_USER_IDS:  # Перевіряємо, чи це адміністратор
        await send_random_messages()
    else:
        await message.answer("❌ У вас немає прав для виконання цієї команди.")

# Обробник команди /t для розсилки тексту або фото всім користувачам, крім відправника
@dp.message(Command("t"))
async def broadcast_handler(message: types.Message):
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("❌ У вас немає прав для виконання цієї команди.")
        return

    try:
        users = get_all_users()

        if not users:
            await message.answer("❌ Немає користувачів для розсилки.")
            return

        # **Обробка фото**
        if message.photo:
            photo_id = message.photo[-1].file_id  # Отримуємо фото у найкращій якості
            
            # Видаляємо текст команди `/t` з підпису, якщо він є
            caption = message.caption if message.caption else ""
            caption = caption.replace("/t", "").strip()  # Видаляємо команду та зайві пробіли

            for user in users:
                if user['user_id'] == message.from_user.id:
                    continue  # Пропускаємо відправника

                try:
                    await bot.send_photo(chat_id=user['user_id'], photo=photo_id, caption=caption or None)
                    logging.info(f"📨 Фото надіслано користувачу {user['user_id']}")
                except Exception as e:
                    logging.warning(f"⚠️ Не вдалося надіслати фото користувачу {user['user_id']}: {e}")

            await message.answer("✅ Фото успішно розіслано всім користувачам!")
            return  # ВАЖЛИВО! ВИХОДИМО З ФУНКЦІЇ, ЩОБ НЕ ОБРОБЛЯТИ ТЕКСТ

        # **Обробка тексту (якщо фото немає)**
        text_content = message.text[len("/t"):].strip()  # Видаляємо "/t" і зайві пробіли

        if not text_content:
            await message.answer("❌ Ви не написали текст для розсилки!")
            return

        for user in users:
            if user['user_id'] == message.from_user.id:
                continue  # Пропускаємо відправника

            try:
                await bot.send_message(user['user_id'], text_content)
                logging.info(f"📨 Повідомлення надіслано користувачу {user['user_id']}")
            except Exception as e:
                logging.warning(f"⚠️ Не вдалося надіслати повідомлення користувачу {user['user_id']}: {e}")

        await message.answer("✅ Повідомлення успішно розіслано всім користувачам!")

    except Exception as e:
        await message.answer(f"❌ Помилка при розсилці: {e}")

# Обробник команди /get_users для отримання списку учасників
@dp.message(Command("get_users"))
async def get_users_handler(message: types.Message):
    if message.from_user.id in ADMIN_USER_IDS:  # Перевіряємо, чи це адміністратор
        users = get_all_users()
        if users:
            user_list = "\n".join([f"ID: {user['user_id']}, Ім'я: {user['first_name']}, Нікнейм: @{user['username'] if user['username'] else 'немає'}" for user in users])
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
            # Розділяємо текст команди на частини
            command_parts = message.text.split(maxsplit=1)
            if len(command_parts) < 2:
                await message.answer("❌ Неправильний формат. Використовуйте: /add_user <user_id>")
                return

            # Отримуємо user_id
            user_id = int(command_parts[1])

            # Перевіряємо, чи користувач вже існує
            cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            existing_user = cursor.fetchone()
            if existing_user:
                await message.answer(f"❌ Користувач із ID {user_id} вже існує в базі даних.")
                return

            # Отримуємо інформацію про користувача через Telegram API
            try:
                user = await bot.get_chat(user_id)
                username = user.username if user.username else "немає"
                first_name = user.first_name if user.first_name else "немає"
            except Exception as e:
                await message.answer(f"❌ Не вдалося отримати інформацію про користувача з ID {user_id}: {e}")
                return

            # Додаємо користувача до бази даних
            add_user(user_id, username, first_name)
            await message.answer(f"✅ Користувач доданий:\nID: {user_id}\nІм'я: {first_name}\nНікнейм: @{username}")
        except ValueError:
            await message.answer("❌ Неправильний формат. user_id має бути числом.")
        except Exception as e:
            await message.answer(f"❌ Помилка при додаванні користувача: {e}")
    else:
        await message.answer("❌ У вас немає прав для виконання цієї команди.")

# Обробник команди /remove_user для ручного видалення користувача
@dp.message(Command("remove_user"))
async def remove_user_handler(message: types.Message):
    if message.from_user.id in ADMIN_USER_IDS:  # Перевіряємо, чи це адміністратор
        try:
            # Розділяємо текст команди на частини
            command_parts = message.text.split(maxsplit=1)
            if len(command_parts) < 2:
                await message.answer("❌ Неправильний формат. Використовуйте: /remove_user <user_id>")
                return

            # Отримуємо user_id
            user_id = int(command_parts[1])

            # Перевіряємо, чи користувач існує
            cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            existing_user = cursor.fetchone()
            if not existing_user:
                await message.answer(f"❌ Користувача з ID {user_id} не знайдено в базі даних.")
                return

            # Видаляємо користувача
            remove_user(user_id)
            await message.answer(f"✅ Користувач із ID {user_id} успішно видалений.")
        except ValueError:
            await message.answer("❌ Неправильний формат. user_id має бути числом.")
        except Exception as e:
            await message.answer(f"❌ Помилка при видаленні користувача: {e}")
    else:
        await message.answer("❌ У вас немає прав для виконання цієї команди.")
        
# Обробник кнопок реакції
@router.callback_query(lambda callback: callback.data.startswith("reaction:"))
async def reaction_handler(callback: types.CallbackQuery):
    if callback.data == "reaction:like":
        await callback.answer("❤️ Дякую за твою реакцію!")
        logging.info(f"Користувач {callback.from_user.id} натиснув ❤️")
    elif callback.data == "reaction:new_photo":
        await callback.answer("🔄 Завантажую нове фото...")
        logging.info(f"Користувач {callback.from_user.id} запросив нове фото")

        # Завантажуємо нове фото
        image = get_random_image(query="mountains, sunset, flowers, love")
        if image:
            await bot.send_photo(
                callback.from_user.id,
                photo=image,
                caption="Ось нове фото для вас!",
                reply_markup=create_reaction_keyboard()
            )
        else:
            await callback.message.answer("⚠️ Не вдалося отримати нове фото.")

# Функція для розсилки випадкових приємних повідомлень
async def send_random_messages():
    messages = [
        "Ти чудова!", "Не забувай посміхатися!", "В тебе все вийде!", "Ти особлива!", "Новий день – нові можливості! Лови їх!", 
        "Ти сильніша, ніж думаєш. Усе вийде!", "Сьогодні твій день – зроби його крутим!", "Прокидайся! У світу для тебе є щось особливе!", 
        "Сонце вже світить для тебе – час підкорювати світ!", "Зроби сьогодні те, про що завтра подякуєш собі!",  
        "Твоя енергія – твоя суперсила! Використай її!", "Кожен новий ранок – це шанс почати спочатку!", "Не бійся труднощів – вони роблять тебе сильнішою!", 
        "Сьогодні ти на крок ближче до своєї мрії!", "Дихай глибше, усміхайся ширше – вперед до успіху!", "Світ чекає на твої звершення!", 
        "Будь собою – це вже твоя суперсила!", "Кава, заряд позитиву і вперед до перемог!", "Щасливий день починається з усмішки!", 
        "Не відкладай щастя – створюй його вже сьогодні!",  
        "Роби те, що приносить тобі радість!", "Твої старання обов’язково принесуть плоди!", "Маленькі кроки ведуть до великих перемог!", 
        "Зараз – найкращий час, щоб почати діяти!", "Навіть найтемніший ранок може стати яскравим!", "Відпусти сумніви – вперед до звершень!", 
        "Живи цей день так, щоб увечері сказати: 'Я молодець!'", "Ти заслуговуєш на щасливе і насичене життя!", 
        "Дивись на світ з оптимізмом – він відповість тобі тим самим!", "Кожна твоя дія – це крок до успіху!",  
        "Розправ крила і лети до своєї мрії!", "Ти можеш досягти всього, що задумано!", "Новий день – нові можливості. Вперед!", 
        "Ти неймовірна!", "Вір у себе – ти здатна на більше!", "Ти здолаєш будь-які труднощі!", "Ніколи не здавайся!", 
        "Кожен день – це новий шанс!", "У тебе є все, щоб досягти мети!", "Продовжуй рухатися вперед, ти на правильному шляху!",  
        "Твоя рішучість – твій ключ до успіху!", "Життя дарує тобі безліч можливостей, скористайся ними!", "Не бійся мріяти – мрії здійснюються!", 
        "Ти сильна, навіть коли не відчуваєш це!", "Ти здатна подолати будь-які перешкоди!", "У тебе є все, щоб досягти великих висот!", 
        "Вір у свої сили, і все буде добре!", "Завжди пам’ятай, що ти варта більше!", "Продовжуй розвиватися – кожен крок вперед важливий!", 
        "Ти вже на шляху до великої мети!",  
        "Немає нічого неможливого для того, хто вірить!", "Кожен день – це шанс стати кращою!", "Твоя стійкість захоплює!", 
        "У тебе є все, щоб змінити своє життя на краще!", "Сьогоднішній день – це новий початок!", "Ти не одна – ми всі тут, щоб підтримати тебе!", 
        "Не бійся бути іншою, ти вже унікальна!", "Всі великі досягнення починаються з маленьких кроків!", "Ти – приклад для наслідування!", 
        "Твоя рішучість і сила волі неймовірні!",  
        "Пам’ятай, що ти – невід’ємна частина цього світу!", "Ти вже зробила перший крок, тепер іди далі!", "Підкорюй свої мрії та амбіції!", 
        "Сміливо йди вперед, світ чекає на тебе!", "Ти все здолаєш!", "У тебе є сила зробити цей день особливим!", 
        "Що б не сталося, пам’ятай: ти завжди маєш можливість змінити ситуацію!", "Твоя енергія не має меж!", 
        "Завжди пам’ятай про свою цінність!", "Ти маєш силу змінювати світ на краще!",  
        "Ти справжня героїня у власній історії!", "Сьогодні буде ще один чудовий день!", 
        "Твоя рішучість допоможе тобі подолати будь-які труднощі!", "Ти маєш внутрішню силу, яка допоможе подолати все!", 
        "Ти заслуговуєш на всі найкращі речі в житті!", "Ти – натхнення для багатьох!", "Не бійся змін, вони приводять до великого!", 
        "Твоя ціль зовсім близько, тримайся!", "Ти сильніша, ніж ти думаєш!", "Будь впевнена у собі – ти справжня лідерка!",  
        "У тебе є все для того, щоб створити своє щастя!", "Ти – унікальна, не забувай про це!", "Життя не має меж, і твої можливості – теж!", 
        "Сьогодні саме той день, щоб розпочати новий шлях!", "Ти – чудова, продовжуй працювати над собою!", "Вір у себе, і ти побачиш чудеса!", 
        "Твоя праця обов’язково принесе плоди!", "Не забувай, що ти сильніша за будь-які обставини!", "Твоя енергія може змінити цей світ!", 
        "Ти вже на півшляху до своєї мети!",  
        "У тебе є все для того, щоб бути щасливою!", "Ти народжена для великих справ!", "Кожен крок наближає тебе до мрії!", 
        "Твоя рішучість і віра в себе безцінні!", "Ти справжня борчиня – продовжуй боротися!", "Всі великі досягнення починаються з маленьких кроків!", 
        "Ти здатна на більше, ніж ти думаєш!", "Не бійся труднощів – вони роблять тебе сильнішою!", "Не забувай, що ти здатна змінити світ!", 
        "Ти вже зробила найважчий крок – дій!",  
        "Ти можеш зробити все, що забажаєш!", "Твоя віра в себе – це твоя сила!", "Будь відважною, мрії здійснюються!", 
        "Ти здатна досягти будь-якої вершини!", "Не дозволяй сумнівам зупиняти тебе!", "Кожен день – це шанс стати кращою!", 
        "Ти володієш безмежною енергією!", "У тебе є все для того, щоб здійснити свої мрії!", "Ти здатна підкорити будь-які вершини!",
        "Життя дарує безліч шансів – скористайся ними!", "Перемога починається з віри в себе!", "Новий день принесе нові можливості!", 
        "Сміливо крокуй вперед, успіх уже чекає!", "У кожній трудності прихована сила для росту!", "Розкривай свої можливості – світ належить сміливим!", 
        "Твоя енергія здатна змінити світ!", "Кожен момент вартий того, щоб його пережити!", "Сміх і позитив – найкращий початок дня!", 
        "Усі мрії можуть стати реальністю!", "Сьогодні – саме той день для змін!", "Нехай серце веде до перемог!", 
        "Крок за кроком ти будеш наближатися до мети!", "Вір у свої сили – це твій головний секрет!", "Життя готове подарувати чудеса, треба тільки вірити!", 
        "Твоя впертість дарує великі можливості!", "Сьогоднішній день – це шанс для початку нового!", "Вітаю з новими можливостями!", 
        "Всі великі досягнення починаються з маленьких кроків!", "Світ чекає на твої досягнення!", "Немає нічого неможливого для того, хто вірить!", 
        "Розпочни цей день із великого плану!", "Не зупиняйся, бо попереду нові горизонти!", "Перемога завжди на стороні сміливих!", 
        "Дихай глибше і насолоджуйся кожним моментом!", "Твоя впертість дає сили для великих звершень!", "Кожен день – новий шанс для розвитку!", 
        "Змініть все, що не приносить щастя!", "Життя відкриває перед тобою великі можливості!", "Сміливо вирушай на зустріч до своїх мрій!", 
        "Всі труднощі тимчасові, а твої можливості – безмежні!", "Вір у те, що ти можеш і обов’язково досягнеш мети!", "Сьогодні твій день, лови всі можливості!", 
        "Мрії здійснюються, якщо в них вірити і діяти!", "Не бійтеся робити помилки – вони ведуть до росту!", "Ти здатна на більше, ніж думаєш!", 
        "Сміливість відкриває двері до нових досягнень!", "Робити кроки вперед – це вже перемога!", "У кожній складній ситуації прихована можливість для росту!", 
        "Ніколи не сумнівайся в своїх силах!", "Ти сильна, навіть коли не відчуваєш це!", "Твоя рішучість зробить цей день особливим!", 
        "Будь впевнена в собі – це перший крок до успіху!", "Твоя віра в себе – це твоє найсильніше зброя!", 
        "Не бійтеся бути собою – це ваш шлях до справжньої сили!", "Відкривай серце для нових можливостей!", "Роби те, що любиш, і будеш щасливою!",
        "Працюй над собою, і все прийде в потрібний час!", "Зараз і є найкращий час для змін!", "Життя не чекає, тому крокуй вперед прямо зараз!", 
        "Твоя впертість і відвага відкривають нові горизонти!", "Не зупиняйся, якщо є хоч один шанс зробити більше!", 
        "Твій шлях до успіху починається з маленького кроку!", "Не чекай на ідеальний момент – створюй його!", 
        "Робити перший крок завжди найважче, але він того вартий!", "Ніколи не здавайся – досягнеш своєї мети!", "Усі труднощі можна подолати, якщо йти до кінця!", 
        "Сьогоднішній день – це новий шанс!", "Сміливо йди вперед, попереду – великі досягнення!", "Ніколи не бійся великих мрій!", "Твоя рішучість – це твоя сила!", 
        "Твоя сила і впертість приносять великі плоди!", "Сьогоднішній день – це шанс розпочати нову подорож!", "Не бійтеся змін, вони ведуть до кращого!", 
        "Ти вже на півшляху до своєї мети!", "Життя – це подорож, а не мета!", "Іноді треба просто почати діяти, щоб побачити результат!", 
        "Твоя сила волі – це твій ключ до всього!", "Не сумнівайся в своїх силах – ти можеш все!", "Твій шлях до успіху ще попереду!", 
        "Сьогодні буде ще один чудовий день!", "Твоя рішучість допоможе подолати будь-які труднощі!", "Успіх приходить до тих, хто не боїться працювати!", 
        "Кожен крок до мети – це вже перемога!", "Не бійся складних шляхів, вони ведуть до великих звершень!", "Вір у себе, і всі труднощі зникнуть!", 
        "Твоя енергія здатна змінити будь-яку ситуацію!", "Що б не сталося, твоя сила не згасне!", "Не забувай, що твоя рішучість – це твоя суперсила!", 
        "Ти справжня героїня у власній історії!", "Сміливо йди вперед, світ чекає на тебе!", "Не бійтеся помилок, вони допомагають рости!", 
        "Ти можеш більше, ніж ти думаєш!", "Твоя рішучість і енергія вже ведуть до перемоги!", "Не бійтеся змін – вони завжди ведуть до кращого!", 
        "Твоя рішучість та віра в себе створюють чудеса!", "У тебе є все для того, щоб зробити цей день чудовим!", 
        "Твоя впертість і сміливість роблять тебе незламною!", "Не бійтеся змін, вони допомагають рости!", "Твоя віра в себе – це сила для великих досягнень!", 
        "Життя дарує можливості, треба вірити в них!", "Твоя енергія може змінити цей світ!", "Кожен твій день – це шанс стати кращою версією себе!", 
        "Світ чекає на твої досягнення!", "Немає меж для тих, хто вірить в себе!"
    ]
    for user in get_all_users():
        try:
            message = random.choice(messages)
            image = get_random_image(query="motivation")
            if image:
                await bot.send_photo(
                    user['user_id'],
                    photo=image,
                    caption=message,
                    reply_markup=create_reaction_keyboard()
                )
                logging.info(f"📨 Повідомлення з картинкою надіслано {user['user_id']}")
            else:
                logging.warning("⚠️ Не вдалося отримати зображення з Pixabay.")
        except Exception as e:
            logging.warning(f"⚠️ Не вдалося надіслати {user['user_id']}: {e}")

# Планувальник для щоденних повідомлень
scheduler = AsyncIOScheduler()
scheduler.add_job(send_random_messages, CronTrigger(hour=18, minute=0, timezone=kyiv_tz))

# Основна функція запуску бота
async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
