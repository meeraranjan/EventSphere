from django.urls import path
from . import views
from .views import organizer_dashboard, events_map
urlpatterns = [
    path('dashboard/', organizer_dashboard, name='organizer_dashboard'),
    path('create/', views.create_event, name='create_event'),
    path('my-events/', views.my_events, name='my_events'),
    path('edit/<int:event_id>/', views.edit_event, name='edit_event'),
    path('delete/<int:event_id>/', views.delete_event, name='delete_event'),
    path('map/', events_map, name='events_map'),
]