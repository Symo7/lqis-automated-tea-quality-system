from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("admin-hub/", views.admin_dashboard, name="admin-dashboard"),
]
