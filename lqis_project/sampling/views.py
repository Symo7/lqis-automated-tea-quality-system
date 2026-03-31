import base64
import json
import uuid
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

logger = logging.getLogger(__name__)

from ai_engine.services import run_baseline_prediction
from core.models import Batch, Factory, Supplier, TeaBuyingCenter
from core.permissions import role_required
from sampling.forms import FactoryIntakeSampleForm, SupervisorDecisionForm
from sampling.models import FactoryIntakeSample, SampleDecisionHistory
from sampling.services import calculate_quality, refresh_alerts

@login_required
@role_required("Inspector", "Factory Manager", "Supervisor", "Admin")
def sync_vault_view(request):
    """
    Renders the offline synchronization vault UI, allowing Inspectors
    to view and flush their IndexedDB queues to the central server.
    """
    return render(request, "sampling/sync_vault.html")

@login_required
@role_required("Inspector", "Admin")
def factory_options(request, factory_id: int):
    centers = list(TeaBuyingCenter.objects.filter(factory_id=factory_id).values("id", "name", "code"))
    batches = list(Batch.objects.filter(factory_id=factory_id).values("id", "batch_code", "buying_center_id", "supplier_id"))
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
@transaction.atomic
def sync_submit(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Basic Rate Limiting (2 seconds per user for sync payload)
    cache_key = f"sync_submit_{request.user.id}"
    if cache.get(cache_key):
        logger.warning(f"Rate limit hit by user {request.user.id} on sync_submit")
        return JsonResponse({"error": "Too many requests. Please wait."}, status=429)
    cache.set(cache_key, True, timeout=2)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON payload from user {request.user.id}")
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
        
        # Strict FK validation mimicking the form clean method
        if center.factory_id != factory.id:
            logger.warning(f"Security: User {request.user.id} attempted mismatched Factory/Center")
            return JsonResponse({"error": "Center does not belong to factory."}, status=400)
        if batch.factory_id != factory.id:
            logger.warning(f"Security: User {request.user.id} attempted mismatched Factory/Batch")
            return JsonResponse({"error": "Batch does not belong to factory."}, status=400)
        if batch.supplier_id != supplier.id:
            logger.warning(f"Security: User {request.user.id} attempted mismatched Supplier/Batch")
            return JsonResponse({"error": "Batch does not belong to supplier."}, status=400)
        if batch.buying_center_id != center.id:
            logger.warning(f"Security: User {request.user.id} attempted mismatched Center/Batch")
            return JsonResponse({"error": "Batch does not belong to center."}, status=400)
            
    except (Factory.DoesNotExist, TeaBuyingCenter.DoesNotExist, Supplier.DoesNotExist, Batch.DoesNotExist):
        logger.warning(f"Invalid Master Data payload from user {request.user.id}")
        return JsonResponse({"error": "Referenced master data no longer valid on server."}, status=400)

    image_data = payload.get("image_data_url")
    file_content = None
    if image_data and "," in image_data:
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
    elif not payload.get("manual_override_pluck_score"):
        return JsonResponse({"error": "Missing image data and no manual override provided."}, status=400)

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
    logger.info(f"Sample {sample.id} synced successfully by user {request.user.id}")
    return JsonResponse({"status": "synced", "sample_id": sample.id})


@login_required
@role_required("Inspector", "Supervisor", "Admin")
def sample_list(request):
    decision = request.GET.get("decision", "")
    date_str = request.GET.get("date", "")
    samples = FactoryIntakeSample.objects.select_related(
        "factory", "tea_buying_center", "supplier", "batch", "inspector", "decision_by"
    )
    if decision == "UNDECIDED":
        samples = samples.filter(decision="")
    elif decision:
        samples = samples.filter(decision=decision)
        
    if date_str:
        samples = samples.filter(intake_timestamp__date=date_str)
        
    return render(request, "sampling/sample_list.html", {"samples": samples, "decision_filter": decision, "date_filter": date_str})


@login_required
@role_required("Inspector", "Admin")
@transaction.atomic
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
            logger.info(f"Sample {sample.id} created successfully by user {request.user.id}")
            messages.success(request, "Factory intake sample saved successfully.")
            return redirect("sampling:sample-detail", pk=sample.pk)
        
        logger.warning(f"Form submission failed for user {request.user.id}. Errors: {form.errors.as_json()}")
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
    
    next_pending_sample = None
    if can_decide:
        next_pending_sample = FactoryIntakeSample.objects.filter(decision="").exclude(pk=pk).order_by("intake_timestamp").first()

    return render(
        request,
        "sampling/sample_detail.html",
        {
            "sample": sample,
            "decision_form": SupervisorDecisionForm(instance=sample),
            "can_decide": can_decide,
            "next_pending_sample": next_pending_sample,
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


@login_required
def debug_storage(request):
    """Diagnostic endpoint to check Cloudinary config at runtime."""
    import cloudinary
    import os
    cloud_cfg = cloudinary.config()
    has_url = bool(os.environ.get('CLOUDINARY_URL', ''))
    storage_class = getattr(settings, 'DEFAULT_FILE_STORAGE', 'unknown')
    cloud_storage = getattr(settings, 'CLOUDINARY_STORAGE', {})
    # Check a recent sample's image URL
    recent = FactoryIntakeSample.objects.exclude(leaf_image='').order_by('-id').first()
    img_info = None
    if recent:
        img_info = {
            'sample_id': recent.id,
            'field_value': str(recent.leaf_image),
            'url': recent.leaf_image.url if recent.leaf_image else None,
            'storage_class': type(recent.leaf_image.storage).__name__,
        }
    return JsonResponse({
        'env_CLOUDINARY_URL_set': has_url,
        'env_CLOUDINARY_URL_prefix': os.environ.get('CLOUDINARY_URL', '')[:30] + '...' if has_url else None,
        'DEFAULT_FILE_STORAGE': storage_class,
        'CLOUDINARY_STORAGE': {k: v[:4]+'...' if v else v for k, v in cloud_storage.items()} if cloud_storage else None,
        'cloudinary_config': {
            'cloud_name': cloud_cfg.cloud_name or None,
            'api_key': (cloud_cfg.api_key or '')[:6] + '...' if cloud_cfg.api_key else None,
        },
        'recent_image': img_info,
    })
