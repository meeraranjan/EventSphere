from django.db import models
from accounts.models import UserProfile

# Create your models here.

class EventOrganizer(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    organization_name = models.CharField(max_length=255)
    contact_email = models.EmailField(blank=True, default='')
    phone_number = models.CharField(max_length=20, blank=True, default='')

    def __str__(self):
        return f"{self.organization_name} ({self.profile.user.username})"
