from django.db import models
from accounts.models import UserProfile
from django.conf import settings

# Create your models here.

class EventOrganizer(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    organization_name = models.CharField(max_length=255)
    contact_email = models.EmailField(blank=True, default='')
    phone_number = models.CharField(max_length=20, blank=True, default='')

    def __str__(self):
        return f"{self.organization_name} ({self.profile.user.username})"

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    ticket_url = models.URLField(blank=True, null=True)
    capacity = models.PositiveIntegerField(blank=True, null=True)
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organized_events'
    )

    def __str__(self):
        return self.title