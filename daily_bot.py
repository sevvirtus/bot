# daily_bot.py
import os
import asyncio
import random
from datetime import date, datetime, timezone
import requests
from telegram import Bot
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap

# === Настройки ===
TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")
API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not all([TOKEN, CHAT_ID, API_KEY]):
    raise RuntimeError("Не заданы переменные окружения!")

# Список участников
people = [
    {"имя": "Доктор", "birth": date(1984, 9, 7)},
    {"имя": "Гарибальди", "birth": date(1984, 2, 22)},
    {"имя": "Леха", "birth": date(1989, 8, 27)},
    {"имя": "Шурин", "birth": date(1981, 4, 18)},
    {"имя": "Вандал", "birth": date(1982, 12, 1)},
    {"имя": "Пашкевич", "birth": date(1987, 1, 9)},
]

bot = Bot(token=TOKEN)

# === Вспомогательные функции ===
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
        return f"погода недоступна"

def get_daily_quote():
    try:
        with open("quotes.txt", "r", encoding="utf-8") as f:
            quotes = [q.strip() for q in f if q.strip()]
        return random.choice(quotes) if quotes else "Цитаты кончились :("
    except Exception as e:
        return "Стэтхем молчит..."

def add_quote_to_image(quote: str, image_path: str = "1.jpg") -> io.BytesIO:
    try:
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        width, height = img.size

        # Простой шрифт (работает везде)
        font = ImageFont.load_default()

        # Увеличиваем размер через масштабирование
        def draw_large_text(draw, xy, text, fill, scale=2):
            x, y = xy
            for dx in range(scale):
                for dy in range(scale):
                    draw.text((x + dx, y + dy), text, fill=fill, font=font)

        full_quote = f"«{quote}»"
        lines = textwrap.wrap(full_quote, width=40)
        if len(lines) > 3:
            lines = lines[:3]
            lines[-1] = lines[-1][:20] + "..."

        y_start = (height // 2) - (len(lines) * 10)
        for i, line in enumerate(lines):
            x = (width - len(line) * 6) // 2  # грубая центровка
            # Тень
            draw_large_text(draw, (x + 2, y_start + i * 20 + 2), line, "black")
            # Белый текст
            draw_large_text(draw, (x, y_start + i * 20), line, "white")

        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=90)
        img_bytes.seek(0)
        return img_bytes

    except Exception as e:
        print(f"Ошибка изображения: {e}")
        with open(image_path, "rb") as f:
            return io.BytesIO(f.read())

async def send_morning_message():
    try:
        quote = get_daily_quote()
        image_bytes = add_quote_to_image(quote)

        caption = (
            "Доброе утро ячейка!\n"
            "Никто за ночь не помер?\n"
            "Тогда погнали!\n\n"
            "До очередного устаревания:\n" +
            "\n".join(f'{p["имя"]} — {days_until_birthday(p["birth"])} дней' for p in people) +
            f"\n\nПогода в Севастополе: {get_weather()}\n\n"
            "Хорошего дня пацаны!\n"
            "Не лажайте!"
        )

        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=image_bytes,
            caption=caption[:1024]
        )
        print("✅ Утреннее сообщение отправлено")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

# === Основной цикл ===
async def main():
    print("✅ Бот запущен. Жду 10:00 по Москве...")
    sent_today = False
    while True:
        # Получаем текущее время в UTC
        now_utc = datetime.now(timezone.utc)
        # Переводим в Москву (UTC+3)
        moscow_time = now_utc.astimezone(timezone(offset=timezone.utc.utcoffset(None) or timezone.utc))
        moscow_time = now_utc.replace(tzinfo=None) + timedelta(hours=3)

        current_hour = moscow_time.hour
        current_minute = moscow_time.minute
        current_date = moscow_time.date()

        # Если 10:00–10:02 и ещё не отправляли сегодня
        if current_hour == 10 and 0 <= current_minute <= 2 and not sent_today:
            await send_morning_message()
            sent_today = True
        elif current_hour == 11:  # Сбрасываем флаг после 11:00
            sent_today = False

        await asyncio.sleep(60)  # Проверяем каждую минуту

if __name__ == "__main__":
    asyncio.run(main())
