# thailand_events/urls.py
from django.contrib import admin
from django.urls import path, include
from events.views import check_updates_view, index, run_check_updates_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("check-updates/", check_updates_view, name="check-updates"),
    path("api/check-updates/", run_check_updates_api, name="api-check-updates"),
    path("", index, name="index"),
]
