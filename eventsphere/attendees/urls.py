from django.urls import path
from . import views

urlpatterns = [
    path('<int:attendee_id>/', views.profile_view, name='profile_view'),
    path('<int:attendee_id>/edit/', views.profile_edit, name='profile_edit'),
]
