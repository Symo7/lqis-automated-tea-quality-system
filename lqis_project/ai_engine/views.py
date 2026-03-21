from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from core.permissions import role_required
from sampling.models import FactoryIntakeSample

@login_required
def info(request):
    return render(request, "ai_engine/info.html")

@login_required
@role_required("Factory Manager", "Admin")
def labeling_workspace(request):
    if request.method == "POST":
        sample_id = request.POST.get("sample_id")
        grade = request.POST.get("grade")
        reason = request.POST.get("reason", "")
        
        if sample_id and grade:
            sample = get_object_or_404(FactoryIntakeSample, id=sample_id)
            sample.ai_label_grade = grade
            sample.ai_label_reason = reason
            sample.ai_label_reviewer = request.user
            sample.ai_label_timestamp = timezone.now()
            sample.save(update_fields=["ai_label_grade", "ai_label_reason", "ai_label_reviewer", "ai_label_timestamp"])
        
        return redirect("ai_engine:labeling_workspace")

    # Fetch next unlabeled sample with an image
    sample = FactoryIntakeSample.objects.filter(
        ai_label_grade__isnull=True
    ).exclude(leaf_image="").order_by("intake_timestamp").first()

    unlabeled_count = FactoryIntakeSample.objects.filter(ai_label_grade__isnull=True).exclude(leaf_image="").count()
    labeled_count = FactoryIntakeSample.objects.filter(ai_label_grade__isnull=False).count()

    return render(request, "ai_engine/labeling_workspace.html", {
        "sample": sample,
        "unlabeled_count": unlabeled_count,
        "labeled_count": labeled_count,
    })


@login_required
@role_required("Admin")
def dataset_export_api(request):
    """
    Provide a JSON endpoint for external MLOps pipelines (e.g. SageMaker)
    to automatically sync the latest human-labeled ground truth dataset.
    """
    labeled_samples = FactoryIntakeSample.objects.filter(
        ai_label_grade__isnull=False
    ).exclude(leaf_image="").select_related("factory", "supplier")

    dataset = []
    for sample in labeled_samples:
        dataset.append({
            "sample_id": sample.id,
            "image_url": request.build_absolute_uri(sample.leaf_image.url),
            "label_grade": sample.ai_label_grade,
            "moisture_pct": float(sample.moisture_pct) if sample.moisture_pct else 0.0,
            "factory_code": sample.factory.code,
            "supplier_name": sample.supplier.name,
            "labeled_at": sample.ai_label_timestamp.isoformat() if sample.ai_label_timestamp else None
        })
    
    return JsonResponse({
        "status": "success",
        "total_labeled": len(dataset),
        "dataset": dataset
    })
