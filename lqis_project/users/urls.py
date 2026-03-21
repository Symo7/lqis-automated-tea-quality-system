from django.urls import path

from .views import demo_login_view, login_view, logout_view

app_name = "users"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("demo/<str:role>/", demo_login_view, name="demo_login"),
]
