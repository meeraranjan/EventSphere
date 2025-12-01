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
from django.core.mail import send_mail
from accounts.models import UserProfile
import math

def haversine(lat1, lon1, lat2, lon2):
    """Return distance in km between two lat/lng points."""
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

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

            # Combine location and city for better geocoding
            full_address = f"{event.location}, {event.city}" if event.city else event.location
            lat, lng = geocode_address(full_address)
            event.latitude = lat
            event.longitude = lng

            event.save()
            messages.success(request, f"'{event.title}' created successfully!")
            return redirect('my_events')
        else:
            print(form.errors)
            messages.error(request, "Please correct the errors below.")
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
            original_event = Event.objects.get(pk=event.pk)

            updated_event = form.save(commit=False)

            if 'location' in form.changed_data or 'city' in form.changed_data:
                full_address = (
                    f"{updated_event.location}, {updated_event.city}"
                    if updated_event.city
                    else updated_event.location
                )
                lat, lng = geocode_address(full_address)
                updated_event.latitude = lat
                updated_event.longitude = lng

            updated_event.save()

            notify = bool(request.POST.get("notify_attendees"))

            if notify:
                field_labels = {
                    "title": "Title",
                    "description": "Description",
                    "location": "Location",
                    "city": "City",
                    "date": "Date",
                    "time": "Time",
                    "price": "Price",
                    "ticket_url": "Ticket link",
                    "capacity": "Capacity",
                    "image": "Image",
                    "category": "Category",
                }

                change_lines = []
                for name in form.changed_data:
                    if name in ["latitude", "longitude"]:
                        continue

                    old_val = getattr(original_event, name, None)
                    new_val = getattr(updated_event, name, None)

                    if name == "category":
                        old_val = dict(Event.CATEGORY_CHOICES).get(old_val, old_val)
                        new_val = dict(Event.CATEGORY_CHOICES).get(new_val, new_val)

                    label = field_labels.get(name, name.replace("_", " ").title())
                    change_lines.append(f"- {label}: {old_val} → {new_val}")

                if not change_lines:
                    change_text = "Details of the changes are not available."
                else:
                    change_text = "\n".join(change_lines)

                rsvps = RSVP.objects.filter(
                    event=updated_event,
                    status__in=[RSVP.GOING, RSVP.INTERESTED],
                ).select_related("attendee")

                recipient_list = []
                for r in rsvps:
                    email = (r.contact_email or getattr(r.attendee, "email", "") or "").strip()
                    if email:
                        recipient_list.append(email)
                        
                recipient_list = sorted(set(recipient_list))

                if recipient_list:
                    subject = f"Update to event '{updated_event.title}'"
                    message = (
                        f"Hello,\n\n"
                        f"The event '{updated_event.title}' that you RSVP'd to has been updated.\n\n"
                        f"Changes:\n{change_text}\n\n"
                        f"Event details:\n"
                        f"- Date: {updated_event.date}\n"
                        f"- Time: {updated_event.time or 'TBA'}\n"
                        f"- Location: {updated_event.location}, {updated_event.city or ''}\n\n"
                        f"— EventSphere Team"
                    )
                    try:
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            recipient_list,
                        )
                    except Exception as e:
                        print(f"[Email Error] Could not send event update notifications: {e}")

            messages.success(request, f"'{updated_event.title}' updated successfully!")
            return redirect('my_events')
        else:
            print(form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = EventForm(instance=event)

    return render(request, 'events/edit_event.html', {'form': form, 'event': event})


def events_map(request):
    filter_form = EventFilterForm(request.GET or None)
    qs = Event.objects.filter(
        approval_status=Event.STATUS_APPROVED,
        date__gte=timezone.localdate()
    ).order_by('date')

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

    # Optional: filter by user location if lat/lng GET params exist
    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')
    max_distance_km = float(request.GET.get('radius') or 50) # default 50 km


    if user_lat and user_lng:
        user_lat, user_lng = float(user_lat), float(user_lng)
        valid_events = [
            event for event in valid_events
            if haversine(user_lat, user_lng, float(event.latitude), float(event.longitude)) <= max_distance_km
        ]

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
            "calendar_url": event.google_calendar_url(),
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

    # Create or update RSVP
    rsvp, created = RSVP.objects.update_or_create(
        event=event,
        attendee=request.user,
        defaults={"status": status, "contact_email": contact_email},
    )

    organizer_email = event.organizer.email
    attendee_email = request.user.email
    attendee_name = request.user.get_full_name() or request.user.username

    # === Email to Organizer ===
    subject_org = f"RSVP Update for '{event.title}'"
    message_org = (
        f"Hello {event.organizer.username},\n\n"
        f"{attendee_name} has {'created' if created else 'updated'} their RSVP for your event '{event.title}'.\n\n"
        f"RSVP status: {rsvp.get_status_display()}\n"
        f"Event date: {event.date}\n"
        f"Location: {event.location}\n\n"
        f"— EventSphere Team"
    )

    # === Email to Attendee ===
    subject_user = f"RSVP Confirmation for '{event.title}'"
    message_user = (
        f"Hello {attendee_name},\n\n"
        f"Your RSVP for '{event.title}' has been {'created' if created else 'updated'} successfully.\n\n"
        f"RSVP status: {rsvp.get_status_display()}\n"
        f"Event date: {event.date}\n"
        f"Location: {event.location}\n\n"
        f"You can view this event under 'My Events' in EventSphere.\n\n"
        f"— EventSphere Team"
    )

    try:
        send_mail(subject_org, message_org, settings.DEFAULT_FROM_EMAIL, [organizer_email])
        send_mail(subject_user, message_user, settings.DEFAULT_FROM_EMAIL, [attendee_email])
    except Exception as e:
        print(f"[Email Error] Could not send RSVP notification: {e}")

    return redirect("events_map")
