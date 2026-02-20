import asyncio
import os
import time
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramRetryAfter
from openai import OpenAI

# -------------------------------
# Переменные окружения
# -------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан! Добавьте его в Variables сервиса Railway.")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY не задан! Добавьте его в Variables сервиса Railway.")

# -------------------------------
# Инициализация бота и OpenAI
# -------------------------------
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------------
# Ограничение скорости сообщений
# -------------------------------
last_message_time = defaultdict(lambda: 0)
MESSAGE_DELAY = 1  # секунда

# Память пользователей, оплативших доступ
paid_users = set()

# -------------------------------
# TON-платёж
# -------------------------------
TON_ADDRESS = "EQCxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # твой TON кошелек
TON_AMOUNT = 1.5  # сумма в TON

# -------------------------------
# Главное меню с кнопками
# -------------------------------
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/start")],
        [KeyboardButton(text="/buy")],
        [KeyboardButton(text="/confirm")],
    ],
    resize_keyboard=True
)

# =========================
# /start — приветствие
# =========================
@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    elapsed = time.time() - last_message_time[user_id]
    if elapsed < MESSAGE_DELAY:
        await asyncio.sleep(MESSAGE_DELAY - elapsed)

    welcome_text = (
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "🤖 <b>AI Бот</b>\n"
        f"Доступ к AI стоит {TON_AMOUNT} TON\n"
        "Используйте кнопки ниже для управления доступом."
    )

    try:
        await message.answer(welcome_text, reply_markup=main_menu)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.timeout)
        await message.answer(welcome_text, reply_markup=main_menu)

    last_message_time[user_id] = time.time()

# =========================
# /buy — отправка ссылки на TON
# =========================
@dp.message(F.text == "/buy")
async def buy(message: Message):
    user_id = message.from_user.id
    elapsed = time.time() - last_message_time[user_id]
    if elapsed < MESSAGE_DELAY:
        await asyncio.sleep(MESSAGE_DELAY - elapsed)

    # Inline кнопка для оплаты TON
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            text=f"Оплатить {TON_AMOUNT} TON",
            url=f"https://ton.org/pay?address={TON_ADDRESS}&amount={TON_AMOUNT}"
        )
    )

    text = (
        f"💰 Оплатите {TON_AMOUNT} TON на кошелек:\n{TON_ADDRESS}\n\n"
        "После подтверждения оплаты нажмите /confirm, чтобы активировать доступ к AI."
    )

    try:
        await message.answer(text, reply_markup=keyboard)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.timeout)
        await message.answer(text, reply_markup=keyboard)

    last_message_time[user_id] = time.time()

# =========================
# /confirm — подтверждение оплаты
# =========================
@dp.message(F.text == "/confirm")
async def confirm_payment(message: Message):
    user_id = message.from_user.id

    # TODO: можно подключить проверку через TON API
    paid_users.add(user_id)

    try:
        await message.answer("✅ Оплата подтверждена! Теперь вы можете писать мне сообщения.", reply_markup=main_menu)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.timeout)
        await message.answer("✅ Оплата подтверждена! Теперь вы можете писать мне сообщения.", reply_markup=main_menu)

# =========================
# AI ответы
# =========================
@dp.message()
async def ai_chat(message: Message):
    user_id = message.from_user.id

    if user_id not in paid_users:
        elapsed = time.time() - last_message_time[user_id]
        if elapsed < MESSAGE_DELAY:
            await asyncio.sleep(MESSAGE_DELAY - elapsed)
        try:
            await message.answer("❌ Сначала оплатите доступ через /buy", reply_markup=main_menu)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.timeout)
            await message.answer("❌ Сначала оплатите доступ через /buy", reply_markup=main_menu)
        last_message_time[user_id] = time.time()
        return

    elapsed = time.time() - last_message_time[user_id]
    if elapsed < MESSAGE_DELAY:
        await asyncio.sleep(MESSAGE_DELAY - elapsed)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты полезный AI ассистент."},
                {"role": "user", "content": message.text},
            ],
            temperature=0.7,
        )

        ai_text = response.choices[0].message.content

        try:
            await message.answer(ai_text)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.timeout)
            await message.answer(ai_text)

    except Exception as e:
        print("AI Error:", str(e))

    last_message_time[user_id] = time.time()

# =========================
# Запуск бота
# =========================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
