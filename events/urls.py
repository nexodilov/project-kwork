from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('check-updates/', views.check_updates_view, name='check-updates'),
]
