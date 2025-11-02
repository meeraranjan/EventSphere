from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
from .models import UserProfile
from attendees.models import Attendee
from events.models import EventOrganizer

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()  # This returns a User instance
            user_type = form.cleaned_data['user_type']
            organization_name = form.cleaned_data.get('organization_name', '')

            user_profile = UserProfile.objects.create(
                user=user,
                contact_email=user.email,
                user_type=user_type,
                organization_name=organization_name if user_type == 'ORGANIZER' else ''
            )

            if user_type == 'ATTENDEE':
                Attendee.objects.create(
                    profile=user_profile,
                    name=user.username,
                    age=form.cleaned_data['age'],
                    email=user.email,
                    phone_number=''
                )

            elif user_type == 'ORGANIZER':
                EventOrganizer.objects.create(
                    profile=user_profile,
                    organization_name=form.cleaned_data['organization_name'],
                    contact_email=user.email,
                    phone_number=''
                )

            return redirect('login')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    error = None
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            try:
                profile = UserProfile.objects.get(user=user)
                if profile.user_type == 'ORGANIZER':
                    return redirect('organizer_dashboard')
                else:
                    attendee = Attendee.objects.get(profile=profile)
                    return redirect('profile_view', attendee_id=attendee.id)
        else:
            error = "Invalid username or password."

    return render(request, 'accounts/login.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('login')
