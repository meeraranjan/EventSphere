from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
from .models import UserProfile

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            profile = form.save()
            user_type = form.cleaned_data['user_type']
            UserProfile.objects.create(
                user=profile,
                contact_email=profile.email,
                user_type=user_type
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
                    return redirect('attendee_profile')
            except UserProfile.DoesNotExist:
                error = "User profile not found."
        else:
            error = "Invalid username or password."

    return render(request, 'accounts/login.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('login')
