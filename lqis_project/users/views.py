from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render


def demo_login_view(request, role):
    """
    Instantly bypasses authentication for investors/stakeholders
    by utilizing the pre-seeded demo accounts.
    """
    User = get_user_model()
    username = f"{role}_1"
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

    return render(request, "users/login.html", {"form": form})


def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect("users:login")
