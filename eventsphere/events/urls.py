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
    path("<int:event_id>/attendees/", views.event_attendees, name="event_attendees"),
    path("<int:event_id>/attendees/export/", views.event_attendees_export_csv, name="event_attendees_export_csv"),
    path("<int:event_id>/rsvp/", views.rsvp_event, name="rsvp_event"),
    path('<int:event_id>/', views.event_detail, name='event_detail'),
    path('<int:event_id>/travel-options/', views.travel_options, name='travel_options'),
]