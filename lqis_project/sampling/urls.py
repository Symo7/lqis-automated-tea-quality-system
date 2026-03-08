from django.urls import path

from . import views

app_name = "sampling"

urlpatterns = [
    path("factory-options/<int:factory_id>/", views.factory_options, name="factory-options"),
    path("", views.sample_list, name="sample-list"),
    path("factory-intake/new/", views.factory_intake_create, name="factory-intake-create"),
    path("prediction-preview/", views.prediction_preview, name="prediction-preview"),
    path("sync-submit/", views.sync_submit, name="sync-submit"),
    path("<int:pk>/", views.sample_detail, name="sample-detail"),
    path("<int:pk>/decision/", views.sample_decision, name="sample-decision"),
]
