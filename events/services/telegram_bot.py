import requests
import io
import os
import tempfile
from PIL import Image
from django.conf import settings


def download_and_convert_image(image_url):
    """Скачать изображение и преобразовать в формат JPEG"""
    if not image_url:
        return None

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://allevents.in/",
        }

        print(f"  📸 Загрузка изображения...")
        response = requests.get(image_url, headers=headers, timeout=20, stream=True)

        if response.status_code == 200:
            # Открыть изображение через PIL
            image = Image.open(io.BytesIO(response.content))

            # Преобразовать в JPEG
            if image.mode in ("RGBA", "LA", "P"):
                # Заменить прозрачный фон на белый
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(
                    image, mask=image.split()[-1] if image.mode == "RGBA" else None
                )
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            # Создать временный файл (JPEG)
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            image.save(tmp_file.name, "JPEG", quality=85, optimize=True)
            tmp_file.close()

            print(f"  ✅ Изображение преобразовано в JPEG: {tmp_file.name}")
            return tmp_file.name

        else:
            print(f"  ⚠️ Не удалось загрузить изображение: {response.status_code}")
            return None

    except Exception as e:
        print(f"  ⚠️ Ошибка загрузки изображения: {e}")
        return None


def send_telegram_photo(message, image_url):
    """Отправить сообщение с изображением в Telegram бот"""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        return False

    tmp_file_path = None

    try:
        # Скачать изображение и преобразовать в JPEG
        tmp_file_path = download_and_convert_image(image_url)

        if not tmp_file_path or not os.path.exists(tmp_file_path):
            print(f"  ⚠️ Файл изображения не найден")
            return False

        url = f"https://api.telegram.org/bot{token}/sendPhoto"

        with open(tmp_file_path, "rb") as f:
            files = {"photo": f}

            data = {"chat_id": chat_id, "caption": message, "parse_mode": "HTML"}

            print(f"  📸 Отправка сообщения с изображением...")
            response = requests.post(url, data=data, files=files, timeout=30)

        if response.status_code == 200:
            print(f"  ✅ Сообщение с изображением отправлено в Telegram")
            return True
        else:
            print(
                f"  ⚠️ Ошибка отправки сообщения с изображением: {response.status_code}"
            )
            return False

    except Exception as e:
        print(f"  ⚠️ Ошибка отправки сообщения с изображением: {e}")
        return False

    finally:
        # Удалить временный файл
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except:
                pass


def send_telegram_text(message):
    """Отправить текстовое сообщение в Telegram бот"""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        return False

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        response = requests.post(url, json=payload, timeout=15)

        if response.status_code == 200:
            print(f"  ✅ Текстовое сообщение отправлено в Telegram")
            return True
        else:
            print(f"  ❌ Ошибка Telegram: {response.status_code}")
            return False

    except Exception as e:
        print(f"  ❌ Ошибка Telegram: {e}")
        return False


def send_new_event_notification(event):
    """Отправить уведомление о новом событии"""
    if event.is_notified:
        return True

    # Время
    start_date_str = event.start_time_display or "Неизвестно"

    # Описание
    description_str = (
        event.description[:200] + "..."
        if len(event.description or "") > 200
        else (event.description or "Нет информации")
    )

    # Текст сообщения
    message = f"""🎉 <b>НОВОЕ СОБЫТИЕ!</b> 🎉

<b>🏙️ Город:</b> {event.city.emoji} {event.city.name}
<b>📌 Название:</b> {event.title}

<b>📅 Время:</b> {start_date_str}
<b>📍 Место:</b> {event.venue or 'Неизвестно'}

<b>🏷️ Категория:</b> {event.category or 'Неизвестно'}

<b>📝 Описание:</b>
{description_str}"""

    if event.event_url:
        message += f"\n\n🔗 <a href='{event.event_url}'>Подробнее</a>"

    # Отправка сообщения
    success = False

    if event.image_url:
        print(f"  📸 Отправка сообщения с изображением...")
        success = send_telegram_photo(message, event.image_url)

        if not success:
            print(f"  📝 Отправка текстового сообщения...")
            success = send_telegram_text(message)
    else:
        print(f"  📝 Отправка текстового сообщения...")
        success = send_telegram_text(message)

    if success:
        event.is_notified = True
        event.save(update_fields=["is_notified"])
        print(f"  ✅ Сообщение отправлено: {event.title[:50]}")
    else:
        print(f"  ⚠️ Сообщение не отправлено: {event.title[:50]}")

    return success
