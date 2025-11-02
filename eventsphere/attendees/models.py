from django.db import models
from accounts.models import UserProfile

class Attendee(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)

    def __str__(self):
        return self.name
