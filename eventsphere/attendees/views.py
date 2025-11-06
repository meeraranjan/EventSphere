from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Attendee
from .forms import AttendeeForm
from django.utils import timezone
from events.models import RSVP, Event

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
    rsvp.delete()
    return redirect('attendee_my_events')
