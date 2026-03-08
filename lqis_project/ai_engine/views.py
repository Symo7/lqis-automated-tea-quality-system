from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def info(request):
    return render(request, "ai_engine/info.html")
