from django.urls import path
from . import views

urlpatterns = [
    path('<int:attendee_id>/', views.profile_view, name='profile_view'),
    path('<int:attendee_id>/edit/', views.profile_edit, name='profile_edit'),
    path('my-events/', views.attendee_my_events, name='attendee_my_events'),
    path('my-events/<int:event_id>/cancel/', views.attendee_cancel_rsvp, name='attendee_cancel_rsvp'),
]
