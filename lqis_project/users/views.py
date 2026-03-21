from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import Http404
from django.shortcuts import redirect, render

import os

DEMO_MODE_ENABLED = os.environ.get('DEMO_MODE_ENABLED', 'False') == 'True'


def demo_login_view(request, role):
    """
    Instantly bypasses authentication for investors/stakeholders
    by utilizing the pre-seeded demo accounts.

    SECURITY: This endpoint is completely disabled unless the
    DEMO_MODE_ENABLED environment variable is explicitly set to 'True'.
    In production, this route returns a hard 404.
    """
    if not DEMO_MODE_ENABLED:
        raise Http404("Demo mode is not enabled on this deployment.")

    User = get_user_model()
    username = f"{role}1"
    demo_user = User.objects.filter(username=username).first()
    
    if demo_user:
        login(request, demo_user)
        request.session['demo_mode'] = True
        messages.info(request, f"Demonstration Simulator Active: Exploring as a {role.title()}.")
        if role.lower() == 'supervisor':
            return redirect("dashboard:overview")
        return redirect("core:home")
        
    messages.error(request, f"Demo Sandbox Offline: Pre-seeded account '{username}' not initialized.")
    return redirect("users:login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:home")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Logged in successfully.")
        return redirect("core:home")

    return render(request, "users/login.html", {"form": form, "demo_mode_enabled": DEMO_MODE_ENABLED})


def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect("users:login")
