import os
import requests
from datetime import date
from telegram import Bot, InputFile
import asyncio
import random
from PIL import Image, ImageDraw, ImageFont
import textwrap
import io

TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")
API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not all([TOKEN, CHAT_ID, API_KEY]):
    raise RuntimeError("Не заданы переменные окружения!")


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


def add_quote_to_image(quote: str, image_path: str = "1.jpg") -> io.BytesIO:
    """Накладывает цитату по центру на изображение с тенью."""
    try:
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        width, height = img.size

        # Попытка загрузить шрифт (если есть) — для GitHub Actions используем fallback
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
        except OSError:
            try:
                font = ImageFont.truetype("NotoSans-Bold.ttf", 48)
            except OSError:
                # Fallback: стандартный шрифт + увеличение масштаба
                font = ImageFont.load_default()
                # Увеличиваем размер через масштабирование
                font = ImageFont.truetype("DejaVuSans-Bold.ttf", 48) if hasattr(ImageFont, 'truetype') else ImageFont.load_default()

        # Функция для переноса текста по ширине
        def wrap_text(text, font, max_width):
            words = text.split()
            lines = []
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                bbox = draw.textbbox((0, 0), test_line, font=font)
                w = bbox[2] - bbox[0]
                if w <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            return lines

         # Цитата в кавычках
        full_quote = f"«{quote}»"

        # Разбиваем на строки (ширина — 70% от картинки)
        lines = wrap_text(full_quote, font, int(width * 0.7))

        # Увеличиваем максимум строк до 6 (иначе может не поместиться)
        if len(lines) > 6:
            lines = lines[:6]
            lines[-1] = lines[-1][:30] + "..."

        # Вычисляем высоту текста
        line_height = 50
        total_height = len(lines) * line_height

        # Центрируем по вертикали
        y_start = (height // 2) - (total_height // 2)

        # Рисуем каждую строку
        for i, line in enumerate(lines):
            # Тень (чёрный)
            x = (width - draw.textbbox((0, 0), line, font=font)[2]) // 2
            y = y_start + i * line_height
            draw.text((x + 2, y + 2), line, fill="black", font=font)
            # Белый текст
            draw.text((x, y), line, fill="white", font=font)

        # Сохраняем в байты
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=90)
        img_bytes.seek(0)
        return img_bytes

    except Exception as e:
        print(f"⚠️ Ошибка при создании изображения: {e}")
        # Если всё сломалось — отправим исходную картинку
        with open(image_path, "rb") as f:
            return io.BytesIO(f.read())

async def send_message():
    bot = Bot(token=TOKEN)
    try:
        # Получаем цитату
        quote = get_daily_quote()
        if "Цитата дня потерялась" in quote or "кончились" in quote:
            # Если цитата не загрузилась — отправим обычное текстовое сообщение
            text = "Цитата не загрузилась, но утро всё равно доброе!\n\n" + \
                   "До очередного устаревания:\n" + \
                   "\n".join(f'{p["имя"]} — {days_until_birthday(p["birth"])} дней' for p in people) + \
                   f"\n\nПогода: {get_weather()}"
            await bot.send_message(chat_id=CHAT_ID, text=text)
        else:
            # Создаём изображение с цитатой
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
                photo=InputFile(image_bytes, filename="quote.jpg"),
                caption=caption[:1024]  # Telegram ограничивает подпись до 1024 символов
            )
        print("✅ Сообщение с цитатой на фоне отправлено")
    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")
        raise


# Переносим список people внутрь (чтобы был доступен в send_message)
people = [
    {"имя": "Доктор", "birth": date(1984, 9, 7)},
    {"имя": "Гарибальди", "birth": date(1984, 2, 22)},
    {"имя": "Леха", "birth": date(1989, 8, 27)},
    {"имя": "Шурин", "birth": date(1981, 4, 18)},
    {"имя": "Вандал", "birth": date(1982, 12, 1)},
]


if __name__ == "__main__":
    asyncio.run(send_message())


