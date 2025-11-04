from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
import json
from django.utils import timezone
from django.conf import settings
from accounts.models import UserProfile
from .models import EventOrganizer, Event
from .forms import EventOrganizerForm, EventForm
from django.http import HttpResponse
from .utils import geocode_address

# Create your views here.
@login_required
def organizer_dashboard(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return HttpResponseForbidden("User profile not found. Please contact support.")

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

@login_required
def create_event(request):
    if request.user.userprofile.user_type != 'ORGANIZER':
        return redirect('home')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            lat, lng = geocode_address(event.location)
            event.latitude = lat
            event.longitude = lng

            event.save()
            return redirect('my_events')
    else:
        form = EventForm()
    return render(request, 'events/create_event.html', {'form': form})

@login_required
def my_events(request):
    # show only events created by the logged-in organizer
    events = Event.objects.filter(organizer=request.user)
    return render(request, 'events/my_events.html', {'events': events})

@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, organizer=request.user)

    if request.method == 'POST':
        event.delete()
        messages.success(request, f'"{event.title}" has been deleted successfully.')
        return redirect('my_events')

    return render(request, 'events/confirm_delete.html', {'event': event})

@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, organizer=request.user)

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            updated_event = form.save(commit=False)

            # 🔔 (Future placeholder) — send notifications to attendees
            # notify_attendees(updated_event)
            if 'location' in form.changed_data:
                lat, lng = geocode_address(updated_event.location)
                updated_event.latitude = lat
                updated_event.longitude = lng

            updated_event.save()

            messages.success(request, f'"{updated_event.title}" updated successfully!')
            return redirect('my_events')


            return redirect('my_events')
    else:
        form = EventForm(instance=event)

    return render(request, 'events/edit_event.html', {'form': form, 'event': event})
def events_map(request):
    upcoming_events = Event.objects.filter(date__gt=timezone.now()).order_by('date')
    valid_events = [event for event in upcoming_events if event.latitude and event.longitude]
    events_json = json.dumps([
        {
            "title": event.title,
            "description": event.description,
            "date": event.date.strftime("%Y-%m-%d"),
            "time": event.time.strftime("%H:%M") if event.time else None,
            "location_name": event.location,
            "latitude": float(event.latitude),
            "longitude": float(event.longitude),
            "image_url": request.build_absolute_uri(event.image.url) if event.image else None,
        }
        for event in valid_events
    ])
    print(events_json)

    context = {
        "events": valid_events,
        "events_json": events_json,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, "events/events_map.html", context)
