from django.urls import path
from .views import organizer_dashboard
urlpatterns = [
    path('dashboard/', organizer_dashboard, name='organizer_dashboard'),
]