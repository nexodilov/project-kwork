from django.core.management.base import BaseCommand
from events.models import City, Event, MonitorLog
from events.services.scraper import AlleventsScraper
from events.services.telegram_bot import send_new_event_notification


class Command(BaseCommand):
    help = "Однократная проверка событий"

    def handle(self, *args, **options):
        self.ensure_cities()
        self.check_all_cities()

    def ensure_cities(self):
        """Если города не существуют, создать их"""
        default_cities = [
            {"name": "Bangkok", "lat": 13.7367, "lng": 100.5231, "emoji": "🏙️"},
            {"name": "Pattaya", "lat": 12.9236, "lng": 100.8825, "emoji": "🏖️"},
            {"name": "Phuket", "lat": 7.8804, "lng": 98.3923, "emoji": "🏝️"},
        ]
        for city_data in default_cities:
            city, created = City.objects.get_or_create(
                name=city_data["name"],
                defaults={
                    "lat": city_data["lat"],
                    "lng": city_data["lng"],
                    "emoji": city_data["emoji"],
                    "is_active": True,
                },
            )
            if not city.is_active:
                city.is_active = True
                city.save()
                self.stdout.write(self.style.WARNING(f"⚠️ {city.name} активирован"))

    def check_all_cities(self):
        """Проверить все города"""
        cities = City.objects.filter(is_active=True)

        if not cities.exists():
            self.stdout.write(
                self.style.ERROR("❌ Не найдено ни одного активного города!")
            )
            return

        for city in cities:
            self.stdout.write(f"\n🔍 Проверяем {city.name}...")

            try:
                events_found, events_new = self.check_city(city)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {city.name}: {events_found} событий, {events_new} новых"
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Ошибка в {city.name}: {e}"))
                import traceback

                traceback.print_exc()

    def check_city(self, city):
        """Проверить один город"""
        scraper = AlleventsScraper(city.name, float(city.lat), float(city.lng))
        events_data = scraper.fetch_events()

        events_found = len(events_data)
        events_new = 0

        for event_data in events_data:
            event_id = event_data["event_id"]
            try:
                # Проверяем наличие только по event_id
                event = Event.objects.get(event_id=event_id)
                created = False
            except Event.DoesNotExist:
                # Создаем новое событие
                event = Event.objects.create(
                    event_id=event_id,
                    city=city,
                    title=event_data["title"],
                    description=event_data.get("description", ""),
                    start_date=event_data.get("start_date"),
                    start_time_display=event_data.get("start_time_display", ""),
                    end_date=event_data.get("end_date"),
                    end_time_display=event_data.get("end_time_display", ""),
                    venue=event_data.get("venue", ""),
                    address=event_data.get("address", ""),
                    lat=event_data.get("lat"),
                    lng=event_data.get("lng"),
                    category=event_data.get("category", ""),
                    price=event_data.get("price", ""),
                    organizer=event_data.get("organizer", ""),
                    website=event_data.get("website", ""),
                    event_url=event_data.get("event_url", ""),
                    share_url=event_data.get("share_url", ""),
                    ticket_url=event_data.get("ticket_url", ""),
                    image_url=event_data.get("image_url", ""),
                    is_free=event_data.get("is_free", False),
                    interested_count=event_data.get("interested_count", 0),
                    raw_data=event_data.get("raw_data", {}),
                )
                created = True
                events_new += 1
                self.stdout.write(f"  🆕 Новое: {event_data['title'][:50]}")

                try:
                    send_new_event_notification(event)
                except Exception as e:
                    self.stdout.write(f"  ⚠️ Ошибка Telegram: {e}")

            # Если существует, ничего не делаем
            # (если хотите обновлять, можете добавить отдельную часть)

        # Запись лога
        MonitorLog.objects.create(
            city=city,
            status="success",
            message="Проверка выполнена успешно",
            events_found=events_found,
            events_new=events_new,
        )

        return events_found, events_new
