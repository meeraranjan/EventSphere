from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class UserProfile(models.Model):
    USER_TYPE_CHOICES = (
        ('ORGANIZER', 'Organizer'),
        ('ATTENDEE', 'Attendee'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='ATTENDEE')

    def __str__(self):
        return f"{self.organization_name} ({self.user.username})"
