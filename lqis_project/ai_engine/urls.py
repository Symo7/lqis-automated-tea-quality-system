from django.urls import path

from . import views

app_name = "ai_engine"

urlpatterns = [
    path("", views.info, name="info"),
]
