from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Attendee
from .forms import AttendeeForm
from django.utils import timezone
from events.models import RSVP, Event
from django.core.mail import send_mail
from django.conf import settings
@login_required
def profile_view(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)
    return render(request, 'attendees/profile_view.html', {'attendee': attendee})

@login_required
def profile_edit(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)
    if request.method == 'POST':
        form = AttendeeForm(request.POST, instance=attendee)
        if form.is_valid():
            form.save()
            return redirect('profile_view', attendee_id=attendee.id)
    else:
        form = AttendeeForm(instance=attendee)
    return render(request, 'attendees/profile_edit.html', {'form': form})

@login_required
def attendee_my_events(request):
    rsvps = (
        RSVP.objects
        .select_related('event')
        .filter(attendee=request.user, status=RSVP.GOING)
        .order_by('-created_at')
    )

    today = timezone.localdate()
    upcoming = [r.event for r in rsvps if r.event.date >= today]
    past     = [r.event for r in rsvps if r.event.date <  today]

    def sort_key(e):
        return (e.date, e.time or timezone.datetime.min.time())

    context = {
        "events_upcoming": sorted(upcoming, key=sort_key),
        "events_past":     sorted(past, key=sort_key, reverse=True),
    }
    return render(request, 'attendees/my_events.html', context)

@login_required
def attendee_cancel_rsvp(request, event_id):
    rsvp = get_object_or_404(RSVP, event_id=event_id, attendee=request.user)
    event = rsvp.event
    attendee_name = request.user.get_full_name() or request.user.username
    attendee_email = request.user.email
    organizer_email = event.organizer.email

    # Send emails before deleting
    subject_org = f"RSVP Cancellation for '{event.title}'"
    message_org = (
        f"Hello {event.organizer.username},\n\n"
        f"{attendee_name} has cancelled their RSVP for your event '{event.title}'.\n\n"
        f"Event date: {event.date}\n"
        f"Location: {event.location}\n\n"
        f"— EventSphere Team"
    )

    subject_user = f"RSVP Cancelled for '{event.title}'"
    message_user = (
        f"Hello {attendee_name},\n\n"
        f"You have successfully cancelled your RSVP for '{event.title}'.\n\n"
        f"Event date: {event.date}\n"
        f"Location: {event.location}\n\n"
        f"— EventSphere Team"
    )

    try:
        send_mail(subject_org, message_org, settings.DEFAULT_FROM_EMAIL, [organizer_email])
        send_mail(subject_user, message_user, settings.DEFAULT_FROM_EMAIL, [attendee_email])
    except Exception as e:
        print(f"[Email Error] Could not send cancellation emails: {e}")

    rsvp.delete()
    return redirect('attendee_my_events')
