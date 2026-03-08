from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("master-data/", views.master_data, name="master-data"),
    path("master-data/factory/create/", views.create_factory, name="factory-create"),
    path("master-data/buying-center/create/", views.create_buying_center, name="buying-center-create"),
    path("master-data/supplier/create/", views.create_supplier, name="supplier-create"),
    path("master-data/batch/create/", views.create_batch, name="batch-create"),
    path("master-data/threshold/create/", views.create_threshold, name="threshold-create"),
    path("api/master-data-snapshot/", views.master_data_snapshot, name="master-data-snapshot"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("service-worker.js", views.service_worker, name="service-worker"),
    path("offline/", views.offline_page, name="offline"),
]
