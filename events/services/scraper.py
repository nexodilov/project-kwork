import requests
import hashlib
import json
import re
from datetime import datetime


class AlleventsScraper:
    """Скрапер Allevents.in - адаптирован под JSON-структуру"""

    BASE_URL = "https://allevents.in/api/index.php/events/web/qs/trending-events"

    def __init__(self, city_name, lat, lng):
        self.city_name = city_name
        self.lat = lat
        self.lng = lng

        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "referer": "https://allevents.in/",
            "sec-ch-ua": '"Brave";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        }

        self.cookies = {
            "current_lat": str(lat),
            "current_long": str(lng),
            "user_city_query": city_name,
            "user_city": city_name,
        }

        self.params = {
            "lat": str(lat),
            "lng": str(lng),
            "city": city_name,
            "country": "Thailand",
            "limit": "100",
            "offset": "0",
        }

    def fetch_events(self):
        """Получить события из API"""
        try:
            print(f"  📡 Запрос API: {self.city_name}")
            response = requests.get(
                self.BASE_URL,
                headers=self.headers,
                cookies=self.cookies,
                params=self.params,
                timeout=15,
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  ✅ Ответ API получен")

                    if isinstance(data, dict) and "data" in data:
                        events_list = data["data"]
                        print(f"  📊 Найдено: {len(events_list)} событий")

                        if events_list:
                            first = events_list[0]
                            print(f"  🔍 Первое: {first.get('eventname', 'N/A')[:50]}")

                        return self.parse_events(events_list)
                    else:
                        print(f"  ⚠️ Данные не найдены")
                        return []

                except json.JSONDecodeError as e:
                    print(f"  ❌ Ошибка парсинга JSON: {e}")
                    return []
            else:
                print(f"  ❌ HTTP {response.status_code}")
                return []

        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            return []

    def parse_events(self, events_list):
        """Распарсить события из ответа API"""
        events = []

        for event_data in events_list:
            event = self.parse_single_event(event_data)
            if event:
                events.append(event)

        print(f"  📊 Распарсено: {len(events)} событий")
        return events

    def parse_single_event(self, event_data):
        """Распарсить одно событие в соответствии с JSON-структурой"""
        try:
            # ========== 1. ID ==========
            event_id = event_data.get("event_id", "")
            if not event_id:
                title = event_data.get("eventname", "")
                start = event_data.get("start_time", "")
                event_id = hashlib.md5(f"{title}_{start}".encode()).hexdigest()

            # ========== 2. Основная информация ==========
            title = event_data.get("eventname", "")
            if not title:
                title = event_data.get("eventname_raw", "")
            if not title:
                title = "Неизвестно"

            # Описание
            description = event_data.get("eventname_raw", "")
            if not description:
                description = title

            # ========== 3. Время ==========
            start_time = event_data.get("start_time", "")
            start_date = self.parse_timestamp(start_time)
            start_time_display = event_data.get("start_time_display", "")

            end_time = event_data.get("end_time", "")
            end_date = self.parse_timestamp(end_time)
            end_time_display = event_data.get("end_time_display", "")

            # ========== 4. Местоположение ==========
            venue_data = event_data.get("venue", {})
            if isinstance(venue_data, dict):
                venue = venue_data.get("full_address", venue_data.get("street", ""))
                address = venue_data.get("full_address", "")
                lat = venue_data.get("latitude")
                lng = venue_data.get("longitude")
            else:
                venue = event_data.get("location", "")
                address = ""
                lat = event_data.get("lat")
                lng = event_data.get("lng")

            if not venue:
                venue = event_data.get("location", "")

            # ========== 5. URL изображения (правильный формат) ==========
            image_url = self.get_clean_image_url(event_data)

            # ========== 6. Категория ==========
            custom_params = event_data.get("custom_params", {})
            categories = custom_params.get("high_confidence_merged_lookup", "")

            if not categories:
                categories_list = custom_params.get("merged_lookup", [])
                if isinstance(categories_list, list):
                    categories = ", ".join(categories_list[:3])

            if not categories:
                categories_list = event_data.get("categories", [])
                if isinstance(categories_list, list):
                    categories = ", ".join(categories_list)

            # ========== 7. Цена ==========
            tickets = event_data.get("tickets", {})
            has_tickets = tickets.get("has_tickets", False)
            ticket_url = tickets.get("ticket_url", "")

            price = ""
            is_free = False

            if has_tickets and ticket_url:
                price = "Билеты продаются"
            elif has_tickets:
                price = "Билеты продаются"
            else:
                is_free = True
                price = "Бесплатно"

            # ========== 8. Организатор ==========
            organizer_data = event_data.get("organizer", {})
            if isinstance(organizer_data, dict):
                organizer = organizer_data.get("name", "")
            else:
                organizer = event_data.get("organizer", "")

            # ========== 9. URL ==========
            event_url = event_data.get("event_url", "")
            share_url = event_data.get("share_url", "")
            website = event_url or share_url

            # ========== 10. Количество заинтересованных ==========
            interested_count = custom_params.get("total_interested_count", 0)

            # ========== 11. Дополнительная информация ==========
            is_featured = event_data.get("featured", "0") == "1"
            score = event_data.get("score", 0)

            # ========== 12. Словарь события ==========
            event = {
                "event_id": str(event_id),
                "title": title,
                "description": description,
                "start_date": start_date,
                "start_time_display": start_time_display,
                "end_date": end_date,
                "end_time_display": end_time_display,
                "venue": venue,
                "address": address,
                "lat": float(lat) if lat else None,
                "lng": float(lng) if lng else None,
                "category": categories,
                "price": price,
                "organizer": organizer,
                "website": website,
                "event_url": event_url,
                "share_url": share_url,
                "ticket_url": ticket_url,
                "image_url": image_url,
                "is_free": is_free,
                "interested_count": interested_count,
                "is_featured": is_featured,
                "score": score,
                "raw_data": event_data,
            }

            # Отладка: показать, найдено ли изображение
            if image_url:
                print(f"  📸 Изображение найдено: {image_url[:80]}...")
            else:
                print(f"  ⚠️ Изображение не найдено: {title[:50]}")

            return event

        except Exception as e:
            print(f"  ❌ Ошибка парсинга: {e}")
            return None

    def get_clean_image_url(self, event_data):
        """Получить URL изображения в правильном формате"""
        image_url = ""

        # 1. Banner URL (лучший)
        banner_url = event_data.get("banner_url", "")
        if banner_url:
            image_url = self.clean_url(banner_url)
            if image_url:
                return image_url

        # 2. Thumb URL large
        thumb_large = event_data.get("thumb_url_large", "")
        if thumb_large:
            image_url = self.clean_url(thumb_large)
            if image_url:
                return image_url

        # 3. Thumb URL
        thumb_url = event_data.get("thumb_url", "")
        if thumb_url:
            image_url = self.clean_url(thumb_url)
            if image_url:
                return image_url

        return ""

    def clean_url(self, url):
        """Очистить URL и привести к правильному формату"""
        if not url:
            return ""

        # Декодировать URL при необходимости
        try:
            # Если требуется декодирование из base64
            if "aHR0c" in url or "aHROc" in url:
                import base64

                # Извлечь base64 часть из URL
                match = re.search(r"aHR0c[^&?]+", url)
                if match:
                    base64_part = match.group()
                    try:
                        decoded = base64.b64decode(base64_part).decode("utf-8")
                        if decoded.startswith("http"):
                            return decoded
                    except:
                        pass
        except:
            pass

        # Исправить URL
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = "https://allevents.in" + url
        elif not url.startswith("http"):
            url = "https://" + url

        # Убрать query параметры (только для изображений)
        if "generate-image" in url:
            # Динамический генератор изображений, можно использовать
            return url

        # Проверить URL
        if self.is_valid_image_url(url):
            return url

        return ""

    def is_valid_image_url(self, url):
        """Проверить, является ли URL действительным изображением"""
        if not url:
            return False

        url_lower = url.lower()

        # Расширения изображений
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".bmp"]

        for ext in image_extensions:
            if ext in url_lower:
                return True

        # Динамический генератор изображений
        if "generate-image" in url_lower:
            return True

        return False

    def parse_timestamp(self, timestamp):
        """Преобразовать timestamp в datetime"""
        if not timestamp:
            return None

        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp)

            if isinstance(timestamp, str) and timestamp.isdigit():
                return datetime.fromtimestamp(int(timestamp))

            return None
        except:
            return None


# ========== Дополнительные функции ==========


def get_coordinates_from_city(city_name):
    """Получить координаты по названию города через OpenStreetMap Nominatim API"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": f"{city_name}, Thailand", "format": "json", "limit": 1}
        headers = {"User-Agent": "AlleventsScraper/1.0"}

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return lat, lon
    except Exception as e:
        print(f"⚠️ Ошибка получения координат: {e}")

    return None, None


def fetch_trending_events_direct(city_name, lat, lng):
    """Напрямую получить события"""
    scraper = AlleventsScraper(city_name, lat, lng)
    return scraper.fetch_events()
