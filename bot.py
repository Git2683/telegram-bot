import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.exceptions import RetryAfter
from openai import OpenAI
from collections import defaultdict
import time

# -------------------------------
# Проверка переменных окружения
# -------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAYMENTS_PROVIDER_TOKEN = os.getenv("PAYMENTS_PROVIDER_TOKEN")  # можно пустым, если Telegram Stars

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
# Ограничение скорости сообщений (Flood control)
# -------------------------------
last_message_time = defaultdict(lambda: 0)
MESSAGE_DELAY = 1  # секунда между сообщениями для одного пользователя

# Простая память пользователей (для примера)
paid_users = set()

# =========================
# Команда /start
# =========================
@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    elapsed = time.time() - last_message_time[user_id]
    if elapsed < MESSAGE_DELAY:
        await asyncio.sleep(MESSAGE_DELAY - elapsed)
    try:
        await message.answer(
            "🤖 <b>AI Бот</b>\n\n"
            "Доступ к AI стоит 100 ⭐\n"
            "Нажмите /buy чтобы оплатить."
        )
    except RetryAfter as e:
        await asyncio.sleep(e.timeout)
        await message.answer(
            "🤖 <b>AI Бот</b>\n\n"
            "Доступ к AI стоит 100 ⭐\n"
            "Нажмите /buy чтобы оплатить."
        )
    last_message_time[user_id] = time.time()

# =========================
# Команда /buy — отправка счета
# =========================
@dp.message(F.text == "/buy")
async def buy(message: Message):
    user_id = message.from_user.id
    elapsed = time.time() - last_message_time[user_id]
    if elapsed < MESSAGE_DELAY:
        await asyncio.sleep(MESSAGE_DELAY - elapsed)

    prices = [LabeledPrice(label="Доступ к AI", amount=10000)]  # 100.00 RUB или 100 Stars

    try:
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Доступ к AI",
            description="Оплата доступа к AI боту",
            payload="ai_access",
            provider_token=PAYMENTS_PROVIDER_TOKEN or "",
            currency="RUB",  # Для Stars используйте "XTR"
            prices=prices,
            start_parameter="ai-access",
        )
    except RetryAfter as e:
        await asyncio.sleep(e.timeout)
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Доступ к AI",
            description="Оплата доступа к AI боту",
            payload="ai_access",
            provider_token=PAYMENTS_PROVIDER_TOKEN or "",
            currency="RUB",
            prices=prices,
            start_parameter="ai-access",
        )
    last_message_time[user_id] = time.time()

# =========================
# Подтверждение оплаты
# =========================
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    user_id = message.from_user.id
    paid_users.add(user_id)

    elapsed = time.time() - last_message_time[user_id]
    if elapsed < MESSAGE_DELAY:
        await asyncio.sleep(MESSAGE_DELAY - elapsed)

    try:
        await message.answer("✅ Оплата прошла успешно! Теперь можете писать мне сообщения.")
    except RetryAfter as e:
        await asyncio.sleep(e.timeout)
        await message.answer("✅ Оплата прошла успешно! Теперь можете писать мне сообщения.")
    last_message_time[user_id] = time.time()

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
            await message.answer("❌ Сначала оплатите доступ через /buy")
        except RetryAfter as e:
            await asyncio.sleep(e.timeout)
            await message.answer("❌ Сначала оплатите доступ через /buy")
        last_message_time[user_id] = time.time()
        return

    # Минимальная задержка, чтобы не попасть под flood
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
        except RetryAfter as e:
            await asyncio.sleep(e.timeout)
            await message.answer(ai_text)

    except Exception as e:
        # минимальный лог, чтобы Railway не заблокировал
        print("AI Error:", str(e))

    last_message_time[user_id] = time.time()

# =========================
# Запуск бота
# =========================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

