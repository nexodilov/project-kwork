import time
import traceback
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from events.models import City, Event, MonitorLog
from events.services.scraper import AlleventsScraper
from events.services.telegram_bot import send_new_event_notification


class Command(BaseCommand):
    help = "Постоянный мониторинг событий"

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval", type=int, default=300, help="Интервал проверки (секунды)"
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        self.stdout.write(
            self.style.SUCCESS(f"🚀 Мониторинг запущен (интервал: {interval} секунд)")
        )

        while True:
            try:
                self.check_all_cities()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
                traceback.print_exc()

            self.stdout.write(f"⏳ Ожидание {interval} секунд...")
            time.sleep(interval)

    def check_all_cities(self):
        """Проверить все города"""
        cities = City.objects.filter(is_active=True)

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
                MonitorLog.objects.create(city=city, status="error", message=str(e))

    def check_city(self, city):
        """Проверить один город"""
        scraper = AlleventsScraper(city.name, float(city.lat), float(city.lng))
        events_data = scraper.fetch_events()

        events_found = len(events_data)
        events_new = 0

        for event_data in events_data:
            try:
                event, created = Event.objects.get_or_create(
                    event_id=event_data["event_id"],
                    city=city,
                    defaults={
                        "title": event_data["title"],
                        "description": event_data.get("description", ""),
                        "start_date": event_data.get("start_date"),
                        "end_date": event_data.get("end_date"),
                        "venue": event_data.get("venue", ""),
                        "address": event_data.get("address", ""),
                        "lat": event_data.get("lat"),
                        "lng": event_data.get("lng"),
                        "category": event_data.get("category", ""),
                        "price": event_data.get("price", ""),
                        "organizer": event_data.get("organizer", ""),
                        "website": event_data.get("website", ""),
                        "image_url": event_data.get("image_url", ""),
                        "raw_data": event_data.get("raw_data", {}),
                    },
                )

                if created:
                    events_new += 1
                    self.stdout.write(f"  🆕 Новое: {event_data['title'][:50]}")
                    send_new_event_notification(event)
                else:
                    # Обновление
                    updated = False
                    for field in [
                        "title",
                        "description",
                        "start_date",
                        "end_date",
                        "venue",
                        "price",
                    ]:
                        new_val = event_data.get(field)
                        old_val = getattr(event, field)
                        if new_val and new_val != old_val:
                            setattr(event, field, new_val)
                            updated = True
                    if updated:
                        event.save()
                        self.stdout.write(f"  🔄 Обновлено: {event_data['title'][:50]}")

            except IntegrityError:
                self.stdout.write(f"  ⏭️ Уже существует: {event_data['title'][:50]}")

        MonitorLog.objects.create(
            city=city,
            status="success",
            message="Проверка выполнена успешно",
            events_found=events_found,
            events_new=events_new,
        )

        return events_found, events_new
