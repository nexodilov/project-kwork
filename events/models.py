from django.db import models
from django.utils import timezone


class City(models.Model):
    name = models.CharField(max_length=100, unique=True)
    lat = models.DecimalField(max_digits=10, decimal_places=6)
    lng = models.DecimalField(max_digits=10, decimal_places=6)
    emoji = models.CharField(max_length=10, default="🏖️")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ["name"]

    def __str__(self):
        return f"{self.emoji} {self.name}"


class Event(models.Model):
    event_id = models.CharField(max_length=255, unique=True, db_index=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=500, db_index=True)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField(null=True, blank=True, db_index=True)
    start_time_display = models.CharField(max_length=100, blank=True, null=True)
    end_date = models.DateTimeField(null=True, blank=True)
    end_time_display = models.CharField(max_length=100, blank=True, null=True)
    venue = models.CharField(max_length=500, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    lat = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    price = models.CharField(max_length=100, blank=True, null=True)
    organizer = models.CharField(max_length=200, blank=True, null=True)
    website = models.URLField(max_length=2000, blank=True, null=True)
    event_url = models.URLField(max_length=2000, blank=True, null=True)
    share_url = models.URLField(max_length=2000, blank=True, null=True)
    ticket_url = models.URLField(max_length=2000, blank=True, null=True)
    image_url = models.URLField(max_length=2000, blank=True, null=True)
    is_free = models.BooleanField(default=False)
    interested_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    is_notified = models.BooleanField(default=False, db_index=True)
    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_updated = models.DateTimeField(auto_now=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"
        ordering = ["-start_date", "-first_seen"]

    def __str__(self):
        return f"{self.title} - {self.city.name}"

    def save(self, *args, **kwargs):
        """Сохранять дату с часовым поясом"""
        # Сделать start_date aware
        if self.start_date and timezone.is_naive(self.start_date):
            self.start_date = timezone.make_aware(self.start_date)

        # Сделать end_date aware
        if self.end_date and timezone.is_naive(self.end_date):
            self.end_date = timezone.make_aware(self.end_date)

        # Сделать first_seen и last_updated aware
        if self.first_seen and timezone.is_naive(self.first_seen):
            self.first_seen = timezone.make_aware(self.first_seen)

        if self.last_updated and timezone.is_naive(self.last_updated):
            self.last_updated = timezone.make_aware(self.last_updated)

        super().save(*args, **kwargs)


class MonitorLog(models.Model):
    STATUS_CHOICES = [
        ("success", "Успешно"),
        ("error", "Ошибка"),
    ]

    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    message = models.TextField()
    events_found = models.IntegerField(default=0)
    events_new = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Лог мониторинга"
        verbose_name_plural = "Логи мониторинга"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at} - {self.city} - {self.status}"

    def save(self, *args, **kwargs):
        """Сохранять дату с часовым поясом"""
        if self.created_at and timezone.is_naive(self.created_at):
            self.created_at = timezone.make_aware(self.created_at)
        super().save(*args, **kwargs)


# events/models.py - полные модели для RA.CO


class RACOSession(models.Model):
    """Хранить данные сессии RA.CO"""

    name = models.CharField(max_length=100, default="default")
    cookies = models.JSONField(default=dict)
    headers = models.JSONField(default=dict)
    last_updated = models.DateTimeField(auto_now=True)
    is_valid = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Сессия RA.CO"
        verbose_name_plural = "Сессии RA.CO"

    def __str__(self):
        return f"Сессия RA.CO - {self.last_updated}"


class RACOArtist(models.Model):
    """Артисты RA.CO"""

    artist_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    name = models.CharField(max_length=200, db_index=True)

    class Meta:
        verbose_name = "Артист RA.CO"
        verbose_name_plural = "Артисты RA.CO"

    def __str__(self):
        return self.name


class RACOVenue(models.Model):
    """Площадка RA.CO"""

    venue_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=300)
    url = models.URLField(max_length=2000, blank=True, null=True)

    class Meta:
        verbose_name = "Площадка RA.CO"
        verbose_name_plural = "Площадки RA.CO"

    def __str__(self):
        return self.name


class RACOEvent(models.Model):
    """События из RA.CO"""

    # Основные данные
    event_id = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=500, db_index=True)

    # Данные о времени
    date = models.DateField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    listing_date = models.DateTimeField(null=True, blank=True)

    # Место и артисты (внешние ключи)
    venue = models.ForeignKey(
        RACOVenue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    artists = models.ManyToManyField(RACOArtist, blank=True, related_name="events")

    # Дополнительная информация
    flyer_front = models.URLField(max_length=2000, blank=True, null=True)
    is_ticketed = models.BooleanField(default=False)
    interested_count = models.IntegerField(default=0)
    event_url = models.URLField(max_length=2000, blank=True, null=True)

    # Метаданные
    is_notified = models.BooleanField(default=False, db_index=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    raw_data = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Событие RA.CO"
        verbose_name_plural = "События RA.CO"
        ordering = ["-date", "-start_time", "-first_seen"]

    def __str__(self):
        return f"{self.title} - {self.venue.name if self.venue else 'Нет площадки'}"

    def get_artists_list(self):
        """Получить список артистов"""
        return list(self.artists.values_list("name", flat=True))

    def get_formatted_date(self):
        """Получить отформатированную дату"""
        if self.start_time:
            return self.start_time.strftime("%Y-%m-%d %H:%M")
        return self.date.strftime("%Y-%m-%d") if self.date else "Неизвестно"
