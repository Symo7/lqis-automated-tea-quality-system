from django.urls import path

from . import views

app_name = "ai_engine"

urlpatterns = [
    path("", views.info, name="info"),
    path("labeling/", views.labeling_workspace, name="labeling_workspace"),
    path("api/dataset-export/", views.dataset_export_api, name="dataset_export_api"),
]
