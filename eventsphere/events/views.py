from django.contrib.auth.decorators import login_required
from django.contrib import messages
import csv
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
import json
from django.utils import timezone
from django.conf import settings
from accounts.models import UserProfile
from .models import EventOrganizer, Event, RSVP
from .forms import EventOrganizerForm, EventForm, EventFilterForm
from django.http import HttpResponse
from .utils import geocode_address
from django.views.decorators.http import require_POST

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
    filter_form = EventFilterForm(request.GET or None)
    qs = Event.objects.order_by('date').filter(date__gte=timezone.localdate())
    if filter_form.is_valid():
        category = filter_form.cleaned_data.get('category')
        start_date = filter_form.cleaned_data.get('start_date')
        end_date = filter_form.cleaned_data.get('end_date')

        if category:
            qs = qs.filter(category=category)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

    valid_events = [event for event in qs if event.latitude and event.longitude]
    user_rsvp_by_event = {}
    if request.user.is_authenticated:
        event_ids = [e.id for e in valid_events]
        user_rsvp_by_event = {
            r.event_id: r.status
            for r in RSVP.objects.filter(attendee=request.user, event_id__in=event_ids)
        }

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
            'id': event.id,
            "category": getattr(event, "category", None),
        }
        for event in valid_events
    ])

    context = {
        "events": valid_events,
        "events_json": events_json,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "filter_form": filter_form,
        "user_rsvp_by_event": user_rsvp_by_event,
    }
    return render(request, "events/events_map.html", context)

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'events/event_detail.html', {'event': event})
def _require_event_organizer_or_403(request, event_id):
    """Utility: only the event's organizer (or admin/staff) can view attendee info."""
    event = get_object_or_404(Event, id=event_id)
    if not (request.user.is_staff or request.user.is_superuser or event.organizer_id == request.user.id):
        return None, HttpResponseForbidden("Access denied. Organizer only.")
    return event, None

@login_required
def event_attendees(request, event_id):
    """Shows a table of RSVPs for one event."""
    event, deny = _require_event_organizer_or_403(request, event_id)
    if deny:
        return deny
    attendees = RSVP.objects.select_related("attendee").filter(event=event).order_by("-created_at")
    return render(request, "events/event_attendees.html", {"event": event, "attendees": attendees})

@login_required
def event_attendees_export_csv(request, event_id):
    """Exports RSVPs as CSV."""
    event, deny = _require_event_organizer_or_403(request, event_id)
    if deny:
        return deny

    rows = (
        RSVP.objects.select_related("attendee")
        .filter(event=event)
        .values_list(
            "attendee__id",
            "attendee__username",
            "attendee__first_name",
            "attendee__last_name",
            "attendee__email",
            "contact_email",
            "status",
            "created_at",
        )
    )

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="event_{event.id}_attendees.csv"'
    writer = csv.writer(resp)
    writer.writerow([
        "Attendee ID", "Username", "First name", "Last name",
        "User email", "RSVP contact email", "RSVP status", "RSVP created_at"
    ])
    for row in rows:
        writer.writerow(row)
    return resp

@login_required
@require_POST
def rsvp_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    status = request.POST.get("status", RSVP.GOING)
    contact_email = request.POST.get("contact_email", request.user.email or "")
    RSVP.objects.update_or_create(
        event=event,
        attendee=request.user,
        defaults={"status": status, "contact_email": contact_email},
    )
    return redirect("events_map")
