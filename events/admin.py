# events/admin.py - цветная версия
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import City, Event, MonitorLog


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "lat", "lng", "is_active", "events_count"]
    list_filter = ["is_active"]
    search_fields = ["name"]

    def events_count(self, obj):
        count = obj.events.count()
        url = reverse("admin:events_event_changelist") + f"?city__id__exact={obj.id}"
        return format_html('<a href="{}">{}</a>', url, count)

    events_count.short_description = "Количество событий"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "city",
        "start_date",
        "venue",
        "is_notified_status",
        "first_seen",
    ]
    list_filter = ["city", "is_active", "is_notified"]
    search_fields = ["title", "venue"]
    readonly_fields = ["event_id", "first_seen", "last_updated"]
    date_hierarchy = "first_seen"

    def is_notified_status(self, obj):
        """Статус уведомления Telegram - format_html используется корректно"""
        if obj.is_notified:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}</span>',
                "✅ Отправлено",
            )
        else:
            return format_html(
                '<span style="color: orange; font-weight: bold;">{}</span>',
                "⏳ Ожидает",
            )

    is_notified_status.short_description = "Telegram уведомление"
    is_notified_status.admin_order_field = "is_notified"

    actions = ["send_notification_again"]

    def send_notification_again(self, request, queryset):
        """Повторно отправить уведомления для выбранных событий"""
        from .services.telegram_bot import send_new_event_notification

        count = 0
        for event in queryset:
            if not event.is_notified:
                if send_new_event_notification(event):
                    count += 1

        if count > 0:
            self.message_user(request, f"Уведомление отправлено для {count} событий.")
        else:
            self.message_user(
                request,
                "Уведомления не были отправлены ни для одного события.",
                level="warning",
            )

    send_notification_again.short_description = (
        "Отправить уведомление для выбранных событий"
    )


@admin.register(MonitorLog)
class MonitorLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "city", "status", "events_found", "events_new"]
    list_filter = ["status", "city"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"
