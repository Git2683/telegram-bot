import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    LabeledPrice,
    PreCheckoutQuery
)
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from openai import OpenAI

import config

# === Инициализация ===
bot = Bot{
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
}

dp = Dispatcher()
client = OpenAI(api_key=config.OPENAI_API_KEY)

# Простая память пользователей (в продакшене использовать БД)
paid_users = set()

# =========================
#      START
# =========================
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🤖 <b>AI Бот</b>\n\n"
        "Доступ к AI стоит 100 ⭐\n"
        "Нажмите /buy чтобы оплатить."
    )

# =========================
#      ПОКУПКА
# =========================
@dp.message(F.text == "/buy")
async def buy(message: Message):

    prices = [LabeledPrice(label="Доступ к AI", amount=10000)]  # 100.00 RUB или 100 Stars

    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Доступ к AI",
        description="Оплата доступа к AI боту",
        payload="ai_access",
        provider_token=config.PAYMENTS_PROVIDER_TOKEN,  # Для Stars можно ""
        currency="RUB",  # Для Stars используйте "XTR"
        prices=prices,
        start_parameter="ai-access",
    )

# =========================
#      ПОДТВЕРЖДЕНИЕ
# =========================
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# =========================
#      УСПЕШНАЯ ОПЛАТА
# =========================
@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    paid_users.add(message.from_user.id)
    await message.answer("✅ Оплата прошла успешно! Теперь можете писать мне сообщения.")

# =========================
#      AI ОТВЕТ
# =========================
@dp.message()
async def ai_chat(message: Message):
    user_id = message.from_user.id

    if user_id not in paid_users:
        await message.answer("❌ Сначала оплатите доступ через /buy")
        return

    await message.answer("⏳ Думаю...")

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

        await message.answer(ai_text)

    except Exception as e:
        await message.answer(f"Ошибка: {e}")

# =========================
#      ЗАПУСК
# =========================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
