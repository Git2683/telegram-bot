import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("8428844583:AAHoflkJsD8nhJM597h2irp9_ZvRQzf67oY")
OPENAI_API_KEY = os.getenv("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")

# Для Telegram Stars оставьте пустым
PAYMENTS_PROVIDER_TOKEN = os.getenv("2051251535:TEST:0Tk5MDA40DgxLTAwNQ")
