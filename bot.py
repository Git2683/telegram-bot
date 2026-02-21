import asyncio
import os
import time
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    CallbackQuery,
)
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
    raise ValueError("❌ BOT_TOKEN не задан!")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY не задан!")

# -------------------------------
# НАСТРОЙКИ
# -------------------------------
CHANNEL_ID = -1003334403707  # <-- вставь ID канала
CHANNEL_LINK = "https://t.me/ChatGPTcanal"  # <-- ссылка на канал

TON_ADDRESS = "UQDWWcZlo7TV-ukEnBjn5dy8BZfbuGtUfymyNLECDScRfLWH"
TON_AMOUNT = 1.5

MESSAGE_DELAY = 1

# -------------------------------
# Инициализация
# -------------------------------
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_API_KEY)

last_message_time = defaultdict(lambda: 0)
paid_users = set()

# -------------------------------
# Главное меню
# -------------------------------
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/start")],
        [KeyboardButton(text="/buy")],
        [KeyboardButton(text="/confirm")],
    ],
    resize_keyboard=True,
)

# -------------------------------
# Проверка подписки
# -------------------------------
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


# -------------------------------
# Клавиатура подписки
# -------------------------------
def subscription_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub")],
        ]
    )


# =========================
# /start
# =========================
@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id

    if not await check_subscription(user_id):
        await message.answer(
            "❗ Для использования бота подпишитесь на канал.",
            reply_markup=subscription_keyboard(),
        )
        return

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "🤖 <b>AI Бот</b>\n"
        f"Доступ стоит {TON_AMOUNT} TON",
        reply_markup=main_menu,
    )


# =========================
# Проверка кнопки подписки
# =========================
@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery):
    user_id = callback.from_user.id

    if await check_subscription(user_id):
        await callback.message.edit_text(
            "✅ Подписка подтверждена! Теперь используйте /start"
        )
    else:
        await callback.answer("❌ Вы не подписаны!", show_alert=True)


# =========================
# /buy
# =========================
@dp.message(F.text == "/buy")
async def buy(message: Message):
    user_id = message.from_user.id

    if not await check_subscription(user_id):
        await message.answer(
            "❌ Сначала подпишитесь на канал.",
            reply_markup=subscription_keyboard(),
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Оплатить {TON_AMOUNT} TON",
                    url=f"https://ton.org/pay?address={TON_ADDRESS}&amount={TON_AMOUNT}",
                )
            ]
        ]
    )

    await message.answer(
        f"💰 Оплатите {TON_AMOUNT} TON на кошелек:\n<code>{TON_ADDRESS}</code>\n\n"
        "После оплаты нажмите /confirm",
        reply_markup=keyboard,
    )


# =========================
# /confirm
# =========================
@dp.message(F.text == "/confirm")
async def confirm_payment(message: Message):
    user_id = message.from_user.id

    if not await check_subscription(user_id):
        await message.answer(
            "❌ Вы должны быть подписаны на канал.",
            reply_markup=subscription_keyboard(),
        )
        return

    paid_users.add(user_id)

    await message.answer(
        "✅ Оплата подтверждена! Теперь вы можете писать мне.",
        reply_markup=main_menu,
    )


# =========================
# AI чат
# =========================
@dp.message()
async def ai_chat(message: Message):
    user_id = message.from_user.id

    # Проверка подписки
    if not await check_subscription(user_id):
        await message.answer(
            "❌ Вы должны быть подписаны на канал.",
            reply_markup=subscription_keyboard(),
        )
        return

    # Проверка оплаты
    if user_id not in paid_users:
        await message.answer(
            "❌ Сначала оплатите доступ через /buy",
            reply_markup=main_menu,
        )
        return

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
        print("AI Error:", str(e))
        await message.answer("⚠️ Ошибка AI, попробуйте позже.")


# =========================
# Запуск
# =========================
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
