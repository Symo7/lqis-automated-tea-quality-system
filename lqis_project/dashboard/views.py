from collections import defaultdict
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Case, CharField, Count, F, Q, Value, When
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from core.models import Factory, FactoryThreshold
from core.permissions import role_required
from sampling.models import FactoryIntakeSample, QualityAlert


@login_required
@role_required("Supervisor", "Admin")
def overview(request):
    selected_factory = request.GET.get("factory")
    factories = Factory.objects.filter(is_active=True)
    samples = FactoryIntakeSample.objects.select_related("factory", "tea_buying_center", "supplier", "batch")

    if selected_factory:
        samples = samples.filter(factory_id=selected_factory)

    today = timezone.localdate()
    today_samples = samples.filter(intake_timestamp__date=today)
    
    pending_batches = samples.filter(decision="").order_by("intake_timestamp")[:15]
    summary = today_samples.aggregate(
        total=Count("id"),
        avg_pluck=Avg("predicted_pluck_score"),
        avg_moisture=Avg("moisture_pct"),
        avg_foreign=Avg("foreign_matter_pct"),
        avg_quality=Avg("quality_score"),
    )

    seven_days_ago = today - timedelta(days=6)
    trend_qs = (
        samples.filter(intake_timestamp__date__gte=seven_days_ago)
        .annotate(day=TruncDate("intake_timestamp"))
        .values("day")
        .annotate(
            pluck=Avg("predicted_pluck_score"),
            moisture=Avg("moisture_pct"),
            foreign=Avg("foreign_matter_pct"),
            quality=Avg("quality_score"),
        )
        .order_by("day")
    )

    alerts = QualityAlert.objects.select_related("sample", "sample__factory", "sample__tea_buying_center").all()
    if selected_factory:
        alerts = alerts.filter(sample__factory_id=selected_factory)

    thresholds = FactoryThreshold.objects.select_related("factory")
    if selected_factory:
        thresholds = thresholds.filter(factory_id=selected_factory)

    buying_center_perf = (
        samples.values("tea_buying_center__name", "tea_buying_center__id")
        .annotate(
            avg_pluck=Avg("predicted_pluck_score"),
            avg_moisture=Avg("moisture_pct"),
            avg_foreign=Avg("foreign_matter_pct"),
            avg_quality=Avg("quality_score"),
            sample_count=Count("id"),
            reject_count=Count("id", filter=Q(quality_status="Reject")),
            alert_count=Count("alerts", distinct=True),
        )
        .order_by("-avg_quality")
    )

    supplier_perf = (
        samples.values("supplier__name", "supplier__id")
        .annotate(
            avg_quality=Avg("quality_score"),
            avg_pluck=Avg("predicted_pluck_score"),
            avg_moisture=Avg("moisture_pct"),
            avg_foreign=Avg("foreign_matter_pct"),
            issues=Count("id", filter=Q(alerts__isnull=False), distinct=True),
            sample_count=Count("id"),
            reject_count=Count("id", filter=Q(quality_status="Reject")),
        )
        .order_by("-avg_quality")
    )

    factory_comparison = (
        FactoryIntakeSample.objects.values("factory__name", "factory__id")
        .annotate(
            avg_quality=Avg("quality_score"),
            sample_count=Count("id"),
            alert_count=Count("alerts", distinct=True),
            reject_count=Count("id", filter=Q(quality_status="Reject")),
        )
        .order_by("-avg_quality")
    )

    decision_breakdown = (
        samples.annotate(decision_label=Case(When(decision="", then=Value("Undecided")), default=F("decision")))
        .values("decision_label")
        .annotate(total=Count("id"))
        .order_by("decision_label")
    )

    decision_trend_qs = (
        samples.filter(intake_timestamp__date__gte=seven_days_ago)
        .annotate(day=TruncDate("intake_timestamp"))
        .values("day")
        .annotate(
            approved=Count("id", filter=Q(decision="Approve Batch")),
            rejected=Count("id", filter=Q(decision="Reject Batch")),
            resort=Count("id", filter=Q(decision="Send for Re-sorting")),
            hold=Count("id", filter=Q(decision="Hold for Review")),
        )
        .order_by("day")
    )

    decision_by_factory = (
        samples.values("factory__name")
        .annotate(
            approved=Count("id", filter=Q(decision="Approve Batch")),
            rejected=Count("id", filter=Q(decision="Reject Batch")),
            resort=Count("id", filter=Q(decision="Send for Re-sorting")),
            hold=Count("id", filter=Q(decision="Hold for Review")),
        )
        .order_by("factory__name")
    )

    decision_by_center = (
        samples.values("tea_buying_center__name")
        .annotate(
            approved=Count("id", filter=Q(decision="Approve Batch")),
            rejected=Count("id", filter=Q(decision="Reject Batch")),
            resort=Count("id", filter=Q(decision="Send for Re-sorting")),
            hold=Count("id", filter=Q(decision="Hold for Review")),
        )
        .order_by("tea_buying_center__name")
    )

    quality_distribution = (
        samples.annotate(
            band=Case(
                When(quality_score__gte=85, then=Value("85-100")),
                When(quality_score__gte=70, then=Value("70-84")),
                When(quality_score__gte=50, then=Value("50-69")),
                default=Value("0-49"),
                output_field=CharField(),
            )
        )
        .values("band")
        .annotate(total=Count("id"))
        .order_by("band")
    )

    status_distribution = samples.values("quality_status").annotate(total=Count("id")).order_by("quality_status")

    supplier_trend_map = defaultdict(list)
    for row in (
        samples.filter(intake_timestamp__date__gte=seven_days_ago)
        .annotate(day=TruncDate("intake_timestamp"))
        .values("day", "supplier__name")
        .annotate(avg_quality=Avg("quality_score"))
        .order_by("day")
    ):
        supplier_trend_map[row["supplier__name"]].append(
            {"day": row["day"].strftime("%Y-%m-%d"), "avg_quality": round(float(row["avg_quality"] or 0), 2)}
        )

    top_supplier_trends = dict(list(supplier_trend_map.items())[0:4])

    alert_distribution_factory = (
        alerts.values("sample__factory__name", "alert_type").annotate(total=Count("id")).order_by("sample__factory__name", "alert_type")
    )

    context = {
        "factories": factories,
        "selected_factory": str(selected_factory or ""),
        "summary": summary,
        "trend_labels": [x["day"].strftime("%Y-%m-%d") for x in trend_qs],
        "pluck_trend": [round(float(x["pluck"] or 0), 2) for x in trend_qs],
        "moisture_trend": [round(float(x["moisture"] or 0), 2) for x in trend_qs],
        "foreign_trend": [round(float(x["foreign"] or 0), 2) for x in trend_qs],
        "quality_trend": [round(float(x["quality"] or 0), 2) for x in trend_qs],
        "recent_alerts": alerts[:8],
        "alert_counts": alerts.values("alert_type").annotate(total=Count("id")).order_by("alert_type"),
        "thresholds": thresholds,
        "recent_samples": samples[:10],
        "pending_batches": pending_batches,
        "buying_center_perf": list(buying_center_perf),
        "supplier_perf": list(supplier_perf),
        "factory_comparison": list(factory_comparison),
        "decision_breakdown_labels": [x["decision_label"] for x in decision_breakdown],
        "decision_breakdown_values": [x["total"] for x in decision_breakdown],
        "quality_distribution_labels": [x["band"] for x in quality_distribution],
        "quality_distribution_values": [x["total"] for x in quality_distribution],
        "status_distribution_labels": [x["quality_status"] for x in status_distribution],
        "status_distribution_values": [x["total"] for x in status_distribution],
        "decision_trend_labels": [x["day"].strftime("%Y-%m-%d") for x in decision_trend_qs],
        "decision_trend_approved": [x["approved"] for x in decision_trend_qs],
        "decision_trend_rejected": [x["rejected"] for x in decision_trend_qs],
        "decision_trend_resort": [x["resort"] for x in decision_trend_qs],
        "decision_trend_hold": [x["hold"] for x in decision_trend_qs],
        "decision_by_factory": list(decision_by_factory),
        "decision_by_center": list(decision_by_center),
        "supplier_trends": top_supplier_trends,
        "alert_distribution_factory": list(alert_distribution_factory),
    }
    return render(request, "dashboard/overview.html", context)
