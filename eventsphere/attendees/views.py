from django.shortcuts import render, redirect, get_object_or_404
from .models import Attendee
from .forms import AttendeeForm

def profile_view(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)
    return render(request, 'attendees/profile_view.html', {'attendee': attendee})

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
