import requests
import hashlib
import json
from datetime import datetime
import random


class AlleventsAPIClient:
    """API-клиент Allevents.in - для Таиланда"""

    BASE_URL = "https://allevents.in/api/index.php/events/web/qs/trending-events"

    # Заголовки, имитирующие тайландский IP
    THAILAND_HEADERS = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "th-TH,th;q=0.9,en;q=0.8",
        "referer": "https://allevents.in/thailand/",
        "sec-ch-ua": '"Brave";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }

    def __init__(self, city_name, lat, lng):
        self.city_name = city_name
        self.lat = lat
        self.lng = lng

        # Специальные заголовки для Таиланда
        self.headers = self.THAILAND_HEADERS.copy()

        # Куки для Таиланда
        self.cookies = {
            "current_lat": str(lat),
            "current_long": str(lng),
            "user_city": city_name,
            "user_city_query": city_name,
            "user_country": "Thailand",
            "current_country": "TH",
        }

        # Параметры API - для Таиланда
        self.params = {
            "lat": str(lat),
            "lng": str(lng),
            "city": city_name,
            "country": "Thailand",
            "limit": "50",
            "offset": "0",
        }

    def fetch_events(self):
        """Получить события из API"""
        try:
            print(f"  📡 Запрос API: {self.city_name}, Таиланд")

            # Отправка запроса
            response = requests.get(
                self.BASE_URL,
                headers=self.headers,
                cookies=self.cookies,
                params=self.params,
                timeout=15,
                allow_redirects=True,
            )

            print(f"  📡 Статус: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  ✅ Ответ API получен")

                    # Проверка структуры API
                    if isinstance(data, dict):
                        if "data" in data and isinstance(data["data"], list):
                            events_list = data["data"]
                            print(f"  📊 Найдено: {len(events_list)} событий")

                            # Отладка: показать первое событие
                            if events_list:
                                first = events_list[0]
                                event_name = first.get(
                                    "eventname", first.get("title", "N/A")
                                )
                                print(f"  🔍 Первое событие: {event_name[:50]}")

                                # Если приходят события из Узбекистана, это ошибка
                                if (
                                    "uzbekistan" in event_name.lower()
                                    or "tashkent" in event_name.lower()
                                ):
                                    print(
                                        f"  ⚠️ Приходят события из Узбекистана! API определяет геолокацию по IP."
                                    )
                                    print(
                                        f"  💡 Необходимо использовать прокси или VPN."
                                    )

                            return self.parse_events(events_list)
                        else:
                            print(f"  ⚠️ Поле 'data' не найдено или не является списком")
                            print(f"  📊 Ключи: {list(data.keys())}")
                            return []
                    else:
                        print(f"  ⚠️ Ответ не является словарём: {type(data)}")
                        return []

                except json.JSONDecodeError as e:
                    print(f"  ❌ Ошибка парсинга JSON: {e}")
                    return []
            else:
                print(f"  ❌ HTTP {response.status_code}")
                return []

        except Exception as e:
            print(f"  ❌ Ошибка API: {e}")
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
        """Распарсить одно событие"""
        try:
            # Поля из API
            event_id = event_data.get("event_id")
            if not event_id:
                title = event_data.get("eventname", event_data.get("title", ""))
                start = event_data.get("start_time", event_data.get("date", ""))
                event_id = hashlib.md5(f"{title}_{start}".encode()).hexdigest()

            # Название события
            title = event_data.get("eventname", event_data.get("title", ""))
            if not title:
                title = event_data.get("eventname_raw", "")
            if not title:
                title = "Неизвестно"

            # Время
            start_date = self.parse_date(
                event_data.get("start_time")
                or event_data.get("date")
                or event_data.get("start_date")
            )
            end_date = self.parse_date(
                event_data.get("end_time") or event_data.get("end_date")
            )

            # Место
            venue = event_data.get("location", event_data.get("venue", ""))

            # Изображение
            image_url = event_data.get("thumb_url", event_data.get("image", ""))
            if not image_url:
                image_url = event_data.get("thumb_url_large", "")

            event = {
                "event_id": str(event_id),
                "title": title,
                "description": event_data.get("description", ""),
                "start_date": start_date,
                "end_date": end_date,
                "venue": venue,
                "address": event_data.get("address", ""),
                "lat": event_data.get("lat"),
                "lng": event_data.get("lng"),
                "category": event_data.get("category", ""),
                "price": event_data.get("price", ""),
                "organizer": event_data.get("organizer", ""),
                "website": event_data.get("url", event_data.get("website", "")),
                "image_url": image_url,
                "raw_data": event_data,
            }

            return event
        except Exception as e:
            print(f"  ❌ Ошибка парсинга события: {e}")
            return None

    def parse_date(self, date_str):
        """Распарсить дату"""
        if not date_str:
            return None

        try:
            if isinstance(date_str, (int, float)):
                from datetime import datetime

                return datetime.fromtimestamp(date_str)

            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue

            return None
        except:
            return None
