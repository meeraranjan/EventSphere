from django.db import models
from django.db import models
from accounts.models import UserProfile  
from django.contrib import admin

class Attendee(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    email = models.EmailField(blank=True, default='')
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.name

admin.site.register(Attendee)
