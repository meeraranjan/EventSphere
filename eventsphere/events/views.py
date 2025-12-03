from django.contrib.auth.decorators import login_required
from django.contrib import messages
import csv
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
import json
from django.utils import timezone
from django.conf import settings
from accounts.models import UserProfile
from .models import EventOrganizer, Event, RSVP
from .forms import EventOrganizerForm, EventForm, EventFilterForm
from .utils import geocode_address
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from accounts.models import UserProfile
import math
import requests
import re

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
            lat, lng, _ = geocode_address(full_address)
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
                full_address = f"{updated_event.location}, {updated_event.city}" if updated_event.city else updated_event.location
                lat, lng, _ = geocode_address(full_address)
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
                    organizer_email = updated_event.organizer.email
                    if organizer_email:
                        recipient_list.append(organizer_email)

                    recipient_list = sorted(set(recipient_list))

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

                    print("[DEBUG] Sending update email to:", recipient_list)

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
    max_distance_km = float(request.GET.get('radius') or 50)  # default 50 km

    try:
        user_lat = float(user_lat) if user_lat else None
        user_lng = float(user_lng) if user_lng else None
    except ValueError:
        user_lat = None
        user_lng = None

    if user_lat is not None and user_lng is not None:
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
        "user_lat": user_lat,
        "user_lng": user_lng,
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
def event_send_reminder(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if not (request.user.is_staff or request.user.is_superuser or event.organizer_id == request.user.id):
        return HttpResponseForbidden("Access denied. Organizer only.")

    rsvps = RSVP.objects.filter(
        event=event,
        status__in=[RSVP.GOING, RSVP.INTERESTED],
    ).select_related("attendee")

    recipient_list = []
    for r in rsvps:
        email = (r.contact_email or getattr(r.attendee, "email", "") or "").strip()
        if email:
            recipient_list.append(email)

    organizer_email = event.organizer.email
    if organizer_email:
        recipient_list.append(organizer_email)

    recipient_list = sorted(set(recipient_list))

    if not recipient_list:
        messages.warning(request, "No attendees with valid email addresses to remind.")
        return redirect("my_events")

    subject = f"Reminder: '{event.title}' is coming up"
    message = (
        f"Hello,\n\n"
        f"This is a reminder for the event '{event.title}' that you RSVP'd to.\n\n"
        f"Event details:\n"
        f"- Date: {event.date}\n"
        f"- Time: {event.time or 'TBA'}\n"
        f"- Location: {event.location}, {event.city or ''}\n\n"
        f"If you can no longer attend, you can update your RSVP in EventSphere.\n\n"
        f"— EventSphere Team"
    )

    print("[DEBUG] Sending reminder email to:", recipient_list)

    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)
        messages.success(request, f"Reminder sent to {len(recipient_list)} recipient(s).")
    except Exception as e:
        print(f"[Email Error] Could not send reminder emails: {e}")
        messages.error(request, "Could not send reminder emails. Check server logs for details.")

    return redirect("my_events")

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


def parse_duration(duration_str):
    """Parse duration string like '514s' into human-readable format."""
    if not duration_str:
        return "Unknown"
    
    match = re.match(r'(\d+)s?$', str(duration_str))
    if match:
        total_seconds = int(match.group(1))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}min"
        elif minutes > 0:
            return f"{minutes} min"
        else:
            return f"{total_seconds} sec"
    
    return str(duration_str)


def estimate_gas_cost(distance_meters):
    """Estimate gas cost for driving."""
    if distance_meters == 0:
        return {"formatted": "Free", "amount": 0}
    
    distance_miles = distance_meters / 1609.34
    mpg = 25  # Average fuel efficiency
    gas_price = 3.50  # Average gas price per gallon
    cost = distance_miles / mpg * gas_price
    
    return {
        "formatted": f"${cost:.2f}",
        "amount": round(cost, 2)
    }


def estimate_uber_cost(distance_meters):
    """Estimate Uber cost based on distance."""
    if distance_meters == 0:
        return {"formatted": "N/A", "amount": 0}
    
    distance_miles = distance_meters / 1609.34
    
    # Uber pricing: base + per mile + booking fee + surge estimate
    base_fare = 2.50
    per_mile = 1.75
    booking_fee = 2.75
    
    total = base_fare + (distance_miles * per_mile) + booking_fee
    
    return {
        "formatted": f"${total:.2f}",
        "amount": round(total, 2),
        "range": f"${total*.9:.2f} - ${total*1.3:.2f}"  # Show range for surge
    }


def estimate_lyft_cost(distance_meters):
    """Estimate Lyft cost (similar to Uber)."""
    if distance_meters == 0:
        return {"formatted": "N/A", "amount": 0}
    
    distance_miles = distance_meters / 1609.34
    
    # Lyft pricing (slightly different from Uber)
    base_fare = 2.00
    per_mile = 1.65
    service_fee = 3.00
    
    total = base_fare + (distance_miles * per_mile) + service_fee
    
    return {
        "formatted": f"${total:.2f}",
        "amount": round(total, 2),
        "range": f"${total*.9:.2f} - ${total*1.3:.2f}"
    }


def estimate_transit_cost():
    """Standard transit fare."""
    return {
        "formatted": "$2.75",
        "amount": 2.75,
        "note": "Single ride fare"
    }


def get_parking_info(event_lat, event_lng):
    """Get basic parking information near event location."""
    # This is a placeholder - you could integrate with parking APIs
    # For now, return generic info
    return {
        "available": True,
        "estimated_cost": "$10-25",
        "note": "Street and lot parking available nearby"
    }

def travel_options(request, event_id):
    """
    Calculate comprehensive travel options to an event.
    Returns: Drive, Walk, Transit, Bike, Uber, Lyft
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Validate event coordinates
    if event.latitude is None or event.longitude is None:
        return JsonResponse({
            "success": False,
            "error": "Event location coordinates are not available"
        }, status=400)
    
    # Get origin coordinates
    origin_lat = request.GET.get("origin_lat")
    origin_lng = request.GET.get("origin_lng")
    
    origin_formatted_address = None
    if not origin_lat or not origin_lng:
        addr = request.GET.get("origin", "").strip()
        if not addr:
            return JsonResponse({
                "success": False,
                "error": "No origin provided"
            }, status=400)
        
        lat, lng, formatted_addr = geocode_address(addr)
        if lat is None or lng is None:
            return JsonResponse({
                "success": False,
                "error": f"Could not find location: {addr}"
            }, status=400)
        origin_lat, origin_lng = lat, lng
        origin_formatted_address = formatted_addr
    
    try:
        origin_lat = float(origin_lat)
        origin_lng = float(origin_lng)
    except (ValueError, TypeError):
        return JsonResponse({
            "success": False,
            "error": "Invalid coordinates"
        }, status=400)
    
    # Check API key
    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
    if not api_key:
        return JsonResponse({
            "success": False,
            "error": "API key not configured"
        }, status=500)
    
    # Google Routes API setup
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline"
    }
    
    origin = {
        "location": {
            "latLng": {
                "latitude": origin_lat,
                "longitude": origin_lng
            }
        }
    }
    
    destination = {
        "location": {
            "latLng": {
                "latitude": float(event.latitude),
                "longitude": float(event.longitude)
            }
        }
    }
    
    # Define travel modes for Google API
    GOOGLE_MODES = {
        "drive": "DRIVE",
        "walk": "WALK",
        "transit": "TRANSIT",
        "bicycle": "BICYCLE"
    }
    
    travel_options_result = {}
    
    # Query each Google travel mode
    for mode_key, mode_value in GOOGLE_MODES.items():
        body = {
            "origin": origin,
            "destination": destination,
            "travelMode": mode_value
        }
        
        if mode_value == "DRIVE":
            body["routingPreference"] = "TRAFFIC_AWARE_OPTIMAL"
        
        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                travel_options_result[mode_key] = {
                    "available": False,
                    "error": error_msg
                }
                continue
            
            data = response.json()
            
            if "routes" not in data or not data["routes"]:
                travel_options_result[mode_key] = {
                    "available": False,
                    "error": "No route found"
                }
                continue
            
            route = data["routes"][0]
            distance_m = route.get("distanceMeters", 0)
            duration_str = route.get("duration", "")
            polyline = route.get("polyline", {}).get("encodedPolyline", "")
            
            if distance_m > 0:
                distance_km = distance_m / 1000
                distance_mi = distance_m / 1609.34
                distance_display = f"{distance_km:.1f} km ({distance_mi:.1f} mi)"
            else:
                distance_display = "Very close"
            
            duration_display = parse_duration(duration_str)
            
            # Add mode-specific details
            if mode_key == "drive":
                gas_cost = estimate_gas_cost(distance_m)
                parking_info = get_parking_info(event.latitude, event.longitude)
                
                travel_options_result[mode_key] = {
                    "available": True,
                    "distance": distance_display,
                    "distance_meters": distance_m,
                    "distance_miles": distance_mi,
                    "duration": duration_display,
                    "duration_seconds": int(duration_str.replace('s', '')) if duration_str else 0,
                    "gas_cost": gas_cost,
                    "parking": parking_info,
                    "polyline": polyline,
                    "mode": mode_value,
                    "mode_display": "Drive",
                    "icon": "🚗",
                    "deep_link": f"https://www.google.com/maps/dir/?api=1&origin={origin_lat},{origin_lng}&destination={event.latitude},{event.longitude}&travelmode=driving"
                }
            elif mode_key == "walk":
                travel_options_result[mode_key] = {
                    "available": True,
                    "distance": distance_display,
                    "distance_meters": distance_m,
                    "distance_miles": distance_mi,
                    "duration": duration_display,
                    "duration_seconds": int(duration_str.replace('s', '')) if duration_str else 0,
                    "cost": {"formatted": "Free", "amount": 0},
                    "polyline": polyline,
                    "mode": mode_value,
                    "mode_display": "Walk",
                    "icon": "🚶",
                    "deep_link": f"https://www.google.com/maps/dir/?api=1&origin={origin_lat},{origin_lng}&destination={event.latitude},{event.longitude}&travelmode=walking"
                }
            elif mode_key == "transit":
                transit_cost = estimate_transit_cost()
                travel_options_result[mode_key] = {
                    "available": True,
                    "distance": distance_display,
                    "distance_meters": distance_m,
                    "distance_miles": distance_mi,
                    "duration": duration_display,
                    "duration_seconds": int(duration_str.replace('s', '')) if duration_str else 0,
                    "cost": transit_cost,
                    "polyline": polyline,
                    "mode": mode_value,
                    "mode_display": "Public Transit",
                    "icon": "🚌",
                    "deep_link": f"https://www.google.com/maps/dir/?api=1&origin={origin_lat},{origin_lng}&destination={event.latitude},{event.longitude}&travelmode=transit"
                }
            elif mode_key == "bicycle":
                travel_options_result[mode_key] = {
                    "available": True,
                    "distance": distance_display,
                    "distance_meters": distance_m,
                    "distance_miles": distance_mi,
                    "duration": duration_display,
                    "duration_seconds": int(duration_str.replace('s', '')) if duration_str else 0,
                    "cost": {"formatted": "Free", "amount": 0},
                    "polyline": polyline,
                    "mode": mode_value,
                    "mode_display": "Bike",
                    "icon": "🚴",
                    "deep_link": f"https://www.google.com/maps/dir/?api=1&origin={origin_lat},{origin_lng}&destination={event.latitude},{event.longitude}&travelmode=bicycling"
                }
                
        except requests.exceptions.Timeout:
            travel_options_result[mode_key] = {
                "available": False,
                "error": "Request timed out"
            }
        except requests.exceptions.RequestException as e:
            travel_options_result[mode_key] = {
                "available": False,
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            travel_options_result[mode_key] = {
                "available": False,
                "error": f"Error: {str(e)}"
            }
    
    # Add ride-hailing estimates (based on driving route)
    if 'drive' in travel_options_result and travel_options_result['drive'].get('available'):
        drive_distance = travel_options_result['drive'].get('distance_meters', 0)
        drive_duration = travel_options_result['drive'].get('duration', 'Unknown')
        
        # Uber - use web link that works on all devices
        uber_cost = estimate_uber_cost(drive_distance)
        travel_options_result['uber'] = {
            "available": True,
            "distance": travel_options_result['drive']['distance'],
            "distance_meters": drive_distance,
            "distance_miles": travel_options_result['drive'].get('distance_miles', 0),
            "duration": drive_duration,
            "cost": uber_cost,
            "mode": "UBER",
            "mode_display": "Uber",
            "icon": "🚕",
            "deep_link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={origin_lat}&pickup[longitude]={origin_lng}&dropoff[latitude]={event.latitude}&dropoff[longitude]={event.longitude}"
        }
        
        # Lyft - use web link that works on all devices
        lyft_cost = estimate_lyft_cost(drive_distance)
        travel_options_result['lyft'] = {
            "available": True,
            "distance": travel_options_result['drive']['distance'],
            "distance_meters": drive_distance,
            "distance_miles": travel_options_result['drive'].get('distance_miles', 0),
            "duration": drive_duration,
            "cost": lyft_cost,
            "mode": "LYFT",
            "mode_display": "Lyft",
            "icon": "🚖",
            "deep_link": f"https://lyft.com/ride?id=lyft&pickup[latitude]={origin_lat}&pickup[longitude]={origin_lng}&destination[latitude]={event.latitude}&destination[longitude]={event.longitude}"
        }
    else:
        travel_options_result['uber'] = {
            "available": False,
            "error": "Driving route not available"
        }
        travel_options_result['lyft'] = {
            "available": False,
            "error": "Driving route not available"
        }
    
    # Count available modes
    available_modes = [k for k, v in travel_options_result.items() if v.get("available", False)]
    
    response_data = {
        "success": True,
        "event_id": event_id,
        "event_title": event.title,
        "event_location": event.location,
        "event_coordinates": {
            "latitude": float(event.latitude),
            "longitude": float(event.longitude)
        },
        "origin_coordinates": {
            "latitude": origin_lat,
            "longitude": origin_lng
        },
        "travel_options": travel_options_result,
        "available_modes": available_modes,
        "total_modes": len(travel_options_result)
    }
    
    # Include formatted address if available
    if origin_formatted_address:
        response_data["origin_formatted_address"] = origin_formatted_address
    
    return JsonResponse(response_data)