
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from accounts.models import UserProfile
from .models import EventOrganizer
from .forms import EventOrganizerForm

# Create your views here.
@login_required

def organizer_dashboard(request):
    profile = UserProfile.objects.get(user=request.user)

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
