import asyncio
import os
import time
import random
import string
from collections import defaultdict

import requests
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from openai import OpenAI

# -------------------------------
# Переменные окружения
# -------------------------------
BOT_TOKEN = os.getenv("8361410975:AAE3lEQXO3HgzQ6leoGCd4AqSmulEIaTOa8")
OPENAI_API_KEY = os.getenv("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")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1003334403707"))
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/ChatGPTcanal")

TON_ADDRESS = os.getenv("TON_ADDRESS", "UQDWWcZlo7TV-ukEnBjn5dy8BZfbuGtUfymyNLECDScRfLWH")
TON_AMOUNT = float(os.getenv("TON_AMOUNT", 1.5))
TON_API_ENDPOINT = os.getenv("https://toncenter.com/api/v2")  # Chainstack/GetBlock API
TON_API_KEY = os.getenv("341fa91bde22579276cd0d9e49ac19c6343136d27494da8b7fbc4b51e31892cc")  # ключ к TON API

if not BOT_TOKEN or not OPENAI_API_KEY or not TON_API_ENDPOINT or not TON_API_KEY:
    raise ValueError("❌ Не все переменные окружения заданы!")

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

# -------------------------------
# Пользователи
# -------------------------------
paid_users = set()         # доступ разрешён
payment_ids = {}           # уникальные метки {user_id: payment_id}
pending_payments = {}      # ожидают подтверждения {user_id: username/addr}
payment_cache = {}         # кэш проверок TON {user_id: (True/False, timestamp)}

# -------------------------------
# Главное меню
# -------------------------------
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/start")],
        [KeyboardButton(text="/buy")]
    ],
    resize_keyboard=True
)

# =========================
# Генерация уникальной метки
# =========================
def generate_payment_id(user_id: int) -> str:
    token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    payment_ids[user_id] = token
    return token

# =========================
# Проверка TON с кэшированием
# =========================
def check_ton_payment_cached(user_id: int, ton_amount: float) -> bool:
    now = time.time()
    if user_id in payment_cache:
        result, timestamp = payment_cache[user_id]
        if now - timestamp < 180:
            return result

    payment_id = payment_ids.get(user_id)
    if not payment_id:
        payment_cache[user_id] = (False, now)
        return False

    try:
        params = {"address": TON_ADDRESS, "limit": 50}
        headers = {"Authorization": f"Bearer {TON_API_KEY}"}
        response = requests.get(TON_API_ENDPOINT + "/getTransactions", params=params, headers=headers)
        response.raise_for_status()
        txs = response.json()

        for tx in txs:
            in_msg = tx.get("in_msg", {})
            comment = in_msg.get("comment", "")
            amount = float(in_msg.get("value", 0))
            if payment_id in comment and amount >= ton_amount:
                payment_cache[user_id] = (True, now)
                return True

        payment_cache[user_id] = (False, now)
        return False
    except Exception as e:
        print("TON API Error:", e)
        payment_cache[user_id] = (False, now)
        return False

# =========================
# /start — карточка информации
# =========================
@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    elapsed = time.time() - last_message_time[user_id]
    if elapsed < MESSAGE_DELAY:
        await asyncio.sleep(MESSAGE_DELAY - elapsed)

    info_card = (
        "💠 <b>Информация о боте</b>\n"
        "🤖 AI Бот на GPT-5 mini — твой помощник.\n"
        f"💰 Стоимость доступа: <b>{TON_AMOUNT} TON</b>\n"
        f"🔔 Подпишись на канал: {CHANNEL_LINK}\n"
        "📝 Используй /buy для оплаты и автоматической активации доступа.\n"
    )

    await message.answer(info_card, reply_markup=main_menu)
    last_message_time[user_id] = time.time()

# =========================
# /buy — карточка оплаты
# =========================
@dp.message(F.text == "/buy")
async def buy(message: Message):
    user_id = message.from_user.id
    elapsed = time.time() - last_message_time[user_id]
    if elapsed < MESSAGE_DELAY:
        await asyncio.sleep(MESSAGE_DELAY - elapsed)

    # Проверка подписки
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["left", "kicked"]:
            await message.answer(f"❌ Сначала подпишись на канал: {CHANNEL_LINK}", reply_markup=main_menu)
            return
    except Exception:
        await message.answer("❌ Бот должен быть администратором канала для проверки подписки.", reply_markup=main_menu)
        return

    payment_id = generate_payment_id(user_id)
    pending_payments[user_id] = message.from_user.username or str(user_id)

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            text=f"💳 Оплатить {TON_AMOUNT} TON",
            url=f"https://ton.org/pay?address={TON_ADDRESS}&amount={TON_AMOUNT}&comment={payment_id}"
        )
    )

    payment_card = (
        "💎 <b>Оплата доступа</b>\n"
        f"💳 Уникальный код: <b>{payment_id}</b>\n"
        f"💰 Сумма: {TON_AMOUNT} TON\n"
        "✅ После оплаты бот автоматически активирует доступ.\n"
        "🕒 Проверка платежей каждые 60 секунд."
    )

    await message.answer(payment_card, reply_markup=keyboard)
    last_message_time[user_id] = time.time()

# =========================
# AI чат — карточка ответа
# =========================
@dp.message()
async def ai_chat(message: Message):
    user_id = message.from_user.id
    if user_id not in paid_users:
        await message.answer(f"❌ Сначала оплатите доступ через /buy и подпишитесь на канал {CHANNEL_LINK}", reply_markup=main_menu)
        return
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение.")
        return

    elapsed = time.time() - last_message_time[user_id]
    if elapsed < MESSAGE_DELAY:
        await asyncio.sleep(MESSAGE_DELAY - elapsed)

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "Ты полезный AI ассистент."},
                {"role": "user", "content": message.text},
            ],
            temperature=0.7,
            max_tokens=150
        )

        ai_text = response.choices[0].message.content
        ai_card = f"🤖 <b>AI Ответ:</b>\n{ai_text}"
        await message.answer(ai_card)

    except Exception as e:
        await message.answer(f"⚠️ AI ошибка: {str(e)}")

    last_message_time[user_id] = time.time()

# =========================
# Фоновая авто-проверка платежей с кэшированием
# =========================
async def auto_check_payments():
    while True:
        for user_id, username in list(pending_payments.items()):
            if check_ton_payment_cached(user_id, TON_AMOUNT):
                paid_users.add(user_id)
                del pending_payments[user_id]
                try:
                    await bot.send_message(
                        user_id,
                        "✅ <b>Оплата подтверждена автоматически!</b>\nТеперь вы можете писать боту и получать AI ответы.",
                        reply_markup=main_menu
                    )
                except Exception as e:
                    print("Ошибка отправки сообщения:", e)
        await asyncio.sleep(60)

# =========================
# Запуск бота
# =========================
async def main():
    asyncio.create_task(auto_check_payments())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
