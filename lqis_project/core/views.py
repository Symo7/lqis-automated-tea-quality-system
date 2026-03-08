from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from core.forms import BatchForm, FactoryForm, FactoryThresholdForm, SupplierForm, TeaBuyingCenterForm
from core.models import Batch, Factory, FactoryThreshold, Supplier, TeaBuyingCenter
from core.permissions import in_group, role_required
from sampling.models import FactoryIntakeSample, QualityAlert


def _master_data_context():
    return {
        "factories": Factory.objects.all(),
        "buying_centers": TeaBuyingCenter.objects.select_related("factory").all(),
        "suppliers": Supplier.objects.all(),
        "batches": Batch.objects.select_related("factory", "buying_center", "supplier").all(),
        "thresholds": FactoryThreshold.objects.select_related("factory").all(),
    }


@login_required
def home(request):
    role = "Admin"
    if in_group(request.user, ["Inspector"]):
        role = "Inspector"
        landing = "sampling:factory-intake-create"
    elif in_group(request.user, ["Supervisor"]):
        role = "Supervisor"
        landing = "dashboard:overview"
    else:
        landing = "core:master-data"

    context = {
        "landing": landing,
        "role": role,
        "pending_decisions": FactoryIntakeSample.objects.filter(decision="").count(),
        "recent_samples": FactoryIntakeSample.objects.select_related("factory", "batch").all()[:5],
        "recent_alerts": QualityAlert.objects.select_related("sample", "sample__factory").all()[:5],
        "total_today": FactoryIntakeSample.objects.filter(intake_timestamp__date=timezone.localdate()).count(),
    }
    return render(request, "core/home.html", context)


@login_required
@role_required("Admin")
def master_data(request):
    context = _master_data_context()
    context.update(
        {
            "factory_form": FactoryForm(),
            "buying_center_form": TeaBuyingCenterForm(),
            "supplier_form": SupplierForm(),
            "batch_form": BatchForm(),
            "threshold_form": FactoryThresholdForm(),
        }
    )
    return render(request, "core/master_data.html", context)


@login_required
@role_required("Admin")
def create_factory(request):
    form = FactoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Factory created.")
    return redirect("core:master-data")


@login_required
@role_required("Admin")
def create_buying_center(request):
    form = TeaBuyingCenterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tea buying center created.")
    return redirect("core:master-data")


@login_required
@role_required("Admin")
def create_supplier(request):
    form = SupplierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Supplier/Farmer Group created.")
    return redirect("core:master-data")


@login_required
@role_required("Admin")
def create_batch(request):
    form = BatchForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Batch created.")
    return redirect("core:master-data")


@login_required
@role_required("Admin")
def create_threshold(request):
    form = FactoryThresholdForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Factory threshold saved.")
    return redirect("core:master-data")


@login_required
def master_data_snapshot(request):
    factories = list(Factory.objects.filter(is_active=True).values("id", "name", "code"))
    centers = list(TeaBuyingCenter.objects.values("id", "name", "code", "factory_id"))
    suppliers = list(Supplier.objects.values("id", "name", "code"))
    batches = list(Batch.objects.values("id", "batch_code", "factory_id", "buying_center_id", "supplier_id"))
    return JsonResponse(
        {
            "fetched_at": timezone.now().isoformat(),
            "factories": factories,
            "centers": centers,
            "suppliers": suppliers,
            "batches": batches,
        }
    )


def manifest(request):
    return JsonResponse(
        {
            "id": "/",
            "name": "LQIS Quality Control",
            "short_name": "LQIS",
            "description": "Automated tea leaf quality detection and monitoring for factory intake.",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "orientation": "portrait-primary",
            "background_color": "#0f1f17",
            "theme_color": "#2d6a4f",
            "icons": [
                {"src": "/static/images/icons/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
                {
                    "src": "/static/images/icons/icon-maskable.svg",
                    "sizes": "any",
                    "type": "image/svg+xml",
                    "purpose": "maskable",
                },
            ],
        }
    )


def service_worker(request):
    js = render_to_string("core/service_worker.js")
    return HttpResponse(js, content_type="application/javascript")


def offline_page(request):
    return render(request, "core/offline.html")
