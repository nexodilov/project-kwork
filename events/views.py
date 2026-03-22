# events/views.py
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required
from .models import City, Event, MonitorLog
from .services.scraper import AlleventsScraper
from .services.telegram_bot import send_new_event_notification


def ensure_cities():
    """Если города не существуют, создать и активировать их"""
    default_cities = [
        {"name": "Bangkok", "lat": 13.7367, "lng": 100.5231, "emoji": "🏙️"},
        {"name": "Pattaya", "lat": 12.9236, "lng": 100.8825, "emoji": "🏖️"},
        {"name": "Phuket", "lat": 7.8804, "lng": 98.3923, "emoji": "🏝️"},
    ]
    created_any = False
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
        if created:
            created_any = True
        elif not city.is_active:
            city.is_active = True
            city.save()
            created_any = True
    return created_any


@staff_member_required
def check_updates_view(request):
    """Проверить новые события для всех активных городов."""
    # Обеспечить наличие городов
    if ensure_cities():
        messages.info(request, "Города автоматически созданы/активированы.")

    cities = City.objects.filter(is_active=True)
    if not cities.exists():
        messages.warning(request, "Не найдено активных городов для проверки.")
        return redirect(reverse("admin:events_event_changelist"))

    results = []
    for city in cities:
        scraper = AlleventsScraper(city.name, float(city.lat), float(city.lng))
        events_data = scraper.fetch_events()
        new_count = 0
        for event_data in events_data:
            event_id = event_data["event_id"]
            # Проверяем наличие по event_id
            try:
                event = Event.objects.get(event_id=event_id)
                created = False
            except Event.DoesNotExist:
                # Создаём новое событие
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
                new_count += 1
                try:
                    send_new_event_notification(event)
                except Exception:
                    pass  # Игнорируем ошибки отправки Telegram
            # Если существует, ничего не делаем
        results.append(f"{city.name}: {new_count} новых событий")
        MonitorLog.objects.create(
            city=city,
            status="success",
            message="Ручная проверка администратором",
            events_found=len(events_data),
            events_new=new_count,
        )

    messages.success(request, "\n".join(results))
    return redirect(reverse("admin:events_event_changelist"))

def index(request):
    """Main frontend page for events."""
    from django.utils import timezone
    now = timezone.now()
    
    # Query future/active events
    events = Event.objects.filter(
        is_active=True, 
        start_date__gte=now
    ).select_related('city').order_by('start_date')
    
    cities = City.objects.filter(is_active=True).order_by('name')
    selected_city = request.GET.get('city')
    
    if selected_city:
        events = events.filter(city__name=selected_city)
    
    context = {
        'events': events,
        'cities': cities,
        'selected_city': selected_city,
    }
    return render(request, 'events/index.html', context)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
import io

@csrf_exempt
def run_check_updates_api(request):
    """API to manually run check_updates from frontend."""
    if request.method == "POST":
        out = io.StringIO()
        try:
            call_command('check_updates', '--no-color', stdout=out, stderr=out)
            return JsonResponse({'status': 'success', 'message': out.getvalue()})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
