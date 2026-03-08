import base64
import json
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ai_engine.services import run_baseline_prediction
from core.models import Batch, Factory, Supplier, TeaBuyingCenter
from core.permissions import role_required
from sampling.forms import FactoryIntakeSampleForm, SupervisorDecisionForm
from sampling.models import FactoryIntakeSample, SampleDecisionHistory
from sampling.services import calculate_quality, refresh_alerts


@login_required
@role_required("Inspector", "Admin")
def factory_options(request, factory_id: int):
    centers = list(TeaBuyingCenter.objects.filter(factory_id=factory_id).values("id", "name", "code"))
    batches = list(Batch.objects.filter(factory_id=factory_id).values("id", "batch_code"))
    return JsonResponse({"centers": centers, "batches": batches})


@login_required
@role_required("Inspector", "Admin")
def prediction_preview(request):
    if request.method != "POST" or "leaf_image" not in request.FILES:
        return JsonResponse({"error": "Image required."}, status=400)
    result = run_baseline_prediction(request.FILES["leaf_image"])
    return JsonResponse(result)


@login_required
@role_required("Inspector", "Admin")
def sync_submit(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    client_id = payload.get("local_id")
    if not client_id:
        return JsonResponse({"error": "Missing local_id"}, status=400)

    existing = FactoryIntakeSample.objects.filter(client_submission_id=client_id).first()
    if existing:
        return JsonResponse({"status": "duplicate", "sample_id": existing.id})

    try:
        factory = Factory.objects.get(id=payload.get("factory"))
        center = TeaBuyingCenter.objects.get(id=payload.get("tea_buying_center"))
        supplier = Supplier.objects.get(id=payload.get("supplier"))
        batch = Batch.objects.get(id=payload.get("batch"))
    except (Factory.DoesNotExist, TeaBuyingCenter.DoesNotExist, Supplier.DoesNotExist, Batch.DoesNotExist):
        return JsonResponse({"error": "Referenced master data no longer valid on server."}, status=400)

    image_data = payload.get("image_data_url")
    if not image_data or "," not in image_data:
        return JsonResponse({"error": "Missing image data."}, status=400)

    meta, b64 = image_data.split(",", 1)
    ext = "jpg"
    if "image/png" in meta:
        ext = "png"
    elif "image/webp" in meta:
        ext = "webp"

    try:
        file_content = ContentFile(base64.b64decode(b64), name=f"offline-{client_id}.{ext}")
    except Exception:
        return JsonResponse({"error": "Invalid image encoding."}, status=400)

    sample = FactoryIntakeSample(
        factory=factory,
        tea_buying_center=center,
        supplier=supplier,
        batch=batch,
        intake_timestamp=payload.get("intake_timestamp") or timezone.now(),
        inspector=request.user,
        leaf_image=file_content,
        client_submission_id=client_id,
        manual_override_pluck_score=payload.get("manual_override_pluck_score") or None,
        moisture_pct=payload.get("moisture_pct") or 0,
        foreign_matter_pct=payload.get("foreign_matter_pct") or 0,
        notes=payload.get("notes", ""),
    )
    sample.save()
    score, status = calculate_quality(sample)
    sample.quality_score = score
    sample.quality_status = status
    sample.save(update_fields=["quality_score", "quality_status", "updated_at"])
    refresh_alerts(sample)
    return JsonResponse({"status": "synced", "sample_id": sample.id})


@login_required
@role_required("Inspector", "Admin")
def sample_list(request):
    decision = request.GET.get("decision", "")
    samples = FactoryIntakeSample.objects.select_related(
        "factory", "tea_buying_center", "supplier", "batch", "inspector", "decision_by"
    )
    if decision == "UNDECIDED":
        samples = samples.filter(decision="")
    elif decision:
        samples = samples.filter(decision=decision)
    return render(request, "sampling/sample_list.html", {"samples": samples, "decision_filter": decision})


@login_required
@role_required("Inspector", "Admin")
def factory_intake_create(request):
    form = FactoryIntakeSampleForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            sample = form.save(commit=False)
            sample.inspector = request.user
            if not sample.client_submission_id:
                sample.client_submission_id = uuid.uuid4().hex
            sample.save()
            score, status = calculate_quality(sample)
            sample.quality_score = score
            sample.quality_status = status
            sample.save(update_fields=["quality_score", "quality_status", "updated_at"])
            refresh_alerts(sample)
            messages.success(request, "Factory intake sample saved successfully.")
            return redirect("sampling:sample-detail", pk=sample.pk)
        messages.error(request, "Please fix form errors and submit again.")

    return render(request, "sampling/factory_intake_form.html", {"form": form})


@login_required
def sample_detail(request, pk: int):
    sample = get_object_or_404(
        FactoryIntakeSample.objects.select_related(
            "factory", "tea_buying_center", "supplier", "batch", "inspector", "decision_by"
        ).prefetch_related("alerts", "decision_history__decided_by"),
        pk=pk,
    )
    can_decide = request.user.is_superuser or request.user.groups.filter(name__in=["Supervisor", "Admin"]).exists()
    return render(
        request,
        "sampling/sample_detail.html",
        {
            "sample": sample,
            "decision_form": SupervisorDecisionForm(instance=sample),
            "can_decide": can_decide,
        },
    )


@login_required
@role_required("Supervisor", "Admin")
def sample_decision(request, pk: int):
    sample = get_object_or_404(FactoryIntakeSample, pk=pk)
    form = SupervisorDecisionForm(request.POST or None, instance=sample)
    if request.method == "POST" and form.is_valid():
        decision_sample = form.save(commit=False)
        decision_sample.decision_by = request.user
        decision_sample.decision_at = timezone.now()
        decision_sample.save(update_fields=["decision", "decision_reason", "decision_by", "decision_at", "updated_at"])
        SampleDecisionHistory.objects.create(
            sample=sample,
            decision=decision_sample.decision,
            reason=decision_sample.decision_reason,
            decided_by=request.user,
        )
        messages.success(request, "Supervisor decision recorded.")
    return redirect("sampling:sample-detail", pk=pk)
