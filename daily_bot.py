import os
import requests
from datetime import date
from telegram import Bot
import asyncio
import random

# Читаем секреты из переменных окружения
TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")
API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Проверка, что всё задано
if not TOKEN:
    raise RuntimeError("Ошибка: не задан TG_BOT_TOKEN")
if not CHAT_ID:
    raise RuntimeError("Ошибка: не задан TG_CHAT_ID")
if not API_KEY:
    raise RuntimeError("Ошибка: не задан OPENWEATHER_API_KEY")


def days_until_birthday(birth: date):
    today = date.today()
    next_birthday = birth.replace(year=today.year)
    if next_birthday < today:
        next_birthday = birth.replace(year=today.year + 1)
    return (next_birthday - today).days


def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Sevastopol&units=metric&appid={API_KEY}&lang=ru"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"{desc}, {round(temp)}°C"
    except Exception as e:
        return f"не удалось получить погоду ({e})"


def get_daily_quote():
    try:
        with open("quotes.txt", "r", encoding="utf-8") as f:
            quotes = [q.strip() for q in f if q.strip()]
        return random.choice(quotes) if quotes else "Цитаты кончились :("
    except Exception as e:
        return f"Цитата дня потерялась: {e}"


def create_message():
    people = [
        {"имя": "Доктор", "birth": date(1984, 9, 7)},
        {"имя": "Гарибальди", "birth": date(1984, 2, 22)},
        {"имя": "Леха", "birth": date(1989, 8, 27)},
        {"имя": "Шурин", "birth": date(1981, 4, 18)},
        {"имя": "Вандал", "birth": date(1982, 12, 1)},
    ]

    lines = []
    lines.append("Доброе утро ячейка!")
    lines.append("Никто за ночь не помер?")
    lines.append("Тогда погнали!")
    lines.append("")
    lines.append(f"Как говорил Дж. Стэйтем: {get_daily_quote()}")
    lines.append("")
    lines.append("До очередного устаревания:")
    for p in people:
        days = days_until_birthday(p["birth"])
        lines.append(f'{p["имя"]} — {days} дней')
    lines.append("")
    lines.append(f"Погода в Севастополе на сегодня: {get_weather()}")
    lines.append("")
    lines.append("Хорошего дня пацаны!")
    lines.append("Не лажайте!")
    return "\n".join(lines)


async def send_message():
    bot = Bot(token=TOKEN)
    try:
        await bot.send_message(chat_id=CHAT_ID, text=create_message())
        print("✅ Сообщение отправлено")
    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(send_message())