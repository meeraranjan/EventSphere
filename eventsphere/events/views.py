<<<<<<< HEAD
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
=======

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
>>>>>>> 3985b4336692e41465ce14f4512ad10086610b5f
from accounts.models import UserProfile
from .models import EventOrganizer
from .forms import EventOrganizerForm

# Create your views here.
@login_required
<<<<<<< HEAD
def organizer_dashboard(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return HttpResponseForbidden("User profile not found. Please contact support.")
=======

def organizer_dashboard(request):
    profile = UserProfile.objects.get(user=request.user)
>>>>>>> 3985b4336692e41465ce14f4512ad10086610b5f

    if profile.user_type != 'ORGANIZER':
        return HttpResponseForbidden("Access denied. Organizer access only.")

    organizer, created = EventOrganizer.objects.get_or_create(profile=profile)

    if request.method == 'POST':
        form = EventOrganizerForm(request.POST, instance=organizer)
        if form.is_valid():
            form.save()
            return redirect('organizer_dashboard')
    else:
        form = EventOrganizerForm(instance=organizer)

    return render(request, 'events/organizer_dashboard.html', {'form': form})
