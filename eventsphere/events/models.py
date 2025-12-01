from django.db import models
from accounts.models import UserProfile
from django.conf import settings
from django.utils import timezone
from django.contrib import admin
from urllib.parse import urlencode
from datetime import datetime, timedelta
import pytz

# Create your models here.

class EventOrganizer(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    organization_name = models.CharField(max_length=255)
    contact_email = models.EmailField(blank=True, default='')
    phone_number = models.CharField(max_length=20, blank=True, default='')

    def __str__(self):
        return f"{self.organization_name} ({self.profile.user.username})"

class Event(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]
    MUSIC = "music"
    SPORTS = "sports"
    TECH = "tech"
    ART = "art"
    FOOD = "food"
    OTHER = "other"
    CHARITIES = "charities" 

    CATEGORY_CHOICES = [
        (MUSIC, "Music"),
        (SPORTS, "Sports"),
        (TECH, "Tech"),
        (ART, "Art"),
        (FOOD, "Food"),
        (CHARITIES, "Charitable"), 
        (OTHER, "Other"),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=OTHER)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    ticket_url = models.URLField(blank=True, null=True)
    capacity = models.PositiveIntegerField(blank=True, null=True)
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organized_events'
    )
    approval_status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    def __str__(self):
        return self.title
    @property
    def is_upcoming(self):
        return self.date > timezone.localdate()
    def google_calendar_url(self):

        tz_name = getattr(settings, 'TIME_ZONE', 'UTC')
        tz = pytz.timezone(tz_name)

        if self.time:
            local_start = datetime.combine(self.date, self.time)
            if local_start.tzinfo is None:
                local_start = tz.localize(local_start)

            local_end = local_start + timedelta(hours=1)

            start_utc = local_start.astimezone(pytz.utc) 
            end_utc = local_end.astimezone(pytz.utc)

            start_str = start_utc.strftime("%Y%m%dT%H%M%SZ")
            end_str = end_utc.strftime("%Y%m%dT%H%M%SZ")
        else:
            start_str = self.date.strftime('%Y%m%d')
            end_str = (self.date + timedelta(days=1)).strftime('%Y%m%d')

        params = {
            "action": "TEMPLATE",
            "text": self.title,
            "details": self.description or "",
            "location": self.location,
            "dates": f"{start_str}/{end_str}",
        }

        if tz_name:
            params['ctz'] = tz_name

        base = "https://calendar.google.com/calendar/render"
        return f"{base}?{urlencode(params)}"

class RSVP(models.Model):
    GOING = "going"
    INTERESTED = "interested"
    NOT_GOING = "not_going"
    STATUS_CHOICES = [
        (GOING, "Going"),
        (INTERESTED, "Interested"),
        (NOT_GOING, "Not going"),
    ]

    event = models.ForeignKey("Event", on_delete=models.CASCADE, related_name="rsvps")
    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rsvps"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=GOING)
    contact_email = models.EmailField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "attendee")

    def __str__(self):
        return f"{self.attendee} → {self.event} ({self.status})"