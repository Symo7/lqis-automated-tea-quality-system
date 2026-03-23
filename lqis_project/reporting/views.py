import csv
from datetime import datetime, timedelta
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from core.models import Factory, Supplier, TeaBuyingCenter
from core.permissions import role_required
from sampling.models import FactoryIntakeSample, QualityAlert


@login_required
@role_required("Supervisor", "Admin")
def daily_report(request):
    qs = FactoryIntakeSample.objects.select_related("factory", "batch", "supplier", "tea_buying_center", "inspector", "decision_by")

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    factory_id = request.GET.get("factory")
    center_id = request.GET.get("center")
    supplier_id = request.GET.get("supplier")
    decision_status = request.GET.get("decision")
    alert_type = request.GET.get("alert_type")

    if start_date:
        qs = qs.filter(intake_timestamp__date__gte=start_date)
    if end_date:
        qs = qs.filter(intake_timestamp__date__lte=end_date)
    if factory_id:
        qs = qs.filter(factory_id=factory_id)
    if center_id:
        qs = qs.filter(tea_buying_center_id=center_id)
    if supplier_id:
        qs = qs.filter(supplier_id=supplier_id)
    if decision_status == "UNDECIDED":
        qs = qs.filter(decision="")
    elif decision_status:
        qs = qs.filter(decision=decision_status)
    if alert_type:
        qs = qs.filter(alerts__alert_type=alert_type).distinct()

    export = request.GET.get("export")
    if export == "csv":
        return export_csv(qs)
    if export == "xlsx":
        return export_xlsx(qs)
    if export == "pdf":
        return export_pdf(qs)

    decision_summary = qs.values("decision").annotate(total=Count("id")).order_by("decision")
    alert_summary = QualityAlert.objects.filter(sample__in=qs).values("alert_type").annotate(total=Count("id")).order_by("alert_type")

    today = timezone.localdate()
    week_start = today - timedelta(days=6)
    weekly_summary = (
        FactoryIntakeSample.objects.filter(intake_timestamp__date__gte=week_start, intake_timestamp__date__lte=today)
        .values("intake_timestamp__date")
        .annotate(avg_quality=Avg("quality_score"), total=Count("id"), rejects=Count("id", filter=Q(quality_status="Reject")))
        .order_by("intake_timestamp__date")
    )

    rejection_summary = qs.values("factory__name").annotate(rejects=Count("id", filter=Q(quality_status="Reject")), total=Count("id")).order_by("-rejects")

    buying_center_summary = (
        qs.values("tea_buying_center__name")
        .annotate(avg_quality=Avg("quality_score"), total=Count("id"), alerts=Count("alerts", distinct=True))
        .order_by("-avg_quality")
    )

    context = {
        "records": qs[:250],
        "factories": Factory.objects.all(),
        "centers": TeaBuyingCenter.objects.all(),
        "suppliers": Supplier.objects.all(),
        "filters": {
            "start_date": start_date or "",
            "end_date": end_date or "",
            "factory": factory_id or "",
            "center": center_id or "",
            "supplier": supplier_id or "",
            "decision": decision_status or "",
            "alert_type": alert_type or "",
        },
        "summary": {
            "total": qs.count(),
            "avg_quality": qs.aggregate(avg=Avg("quality_score"))["avg"],
            "rejects": qs.filter(quality_status="Reject").count(),
        },
        "decision_summary": decision_summary,
        "alert_summary": alert_summary,
        "weekly_summary": weekly_summary,
        "rejection_summary": rejection_summary,
        "buying_center_summary": buying_center_summary,
    }
    return render(request, "reporting/daily_report.html", context)


def export_csv(qs):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="lqis-report-{timezone.now().strftime("%Y-%m-%d_%H%M")}.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Timestamp",
        "Factory",
        "Center",
        "Supplier",
        "Batch",
        "Pluck",
        "Moisture",
        "Foreign",
        "Quality Score",
        "Quality Status",
        "Decision",
        "Inspector",
        "Decision By",
    ])
    for r in qs:
        writer.writerow(
            [
                r.intake_timestamp,
                r.factory.code,
                r.tea_buying_center.code,
                r.supplier.code,
                r.batch.batch_code,
                r.effective_pluck_score(),
                r.moisture_pct,
                r.foreign_matter_pct,
                r.quality_score,
                r.quality_status,
                r.decision or "Pending",
                r.inspector.username,
                r.decision_by.username if r.decision_by else "",
            ]
        )
    return response


def export_xlsx(qs):
    try:
        from openpyxl import Workbook
    except Exception:
        return export_csv(qs)

    wb = Workbook()
    ws = wb.active
    ws.title = "LQIS Report"
    headers = [
        "Timestamp",
        "Factory",
        "Center",
        "Supplier",
        "Batch",
        "Pluck",
        "Moisture",
        "Foreign",
        "Quality Score",
        "Quality Status",
        "Decision",
        "Inspector",
        "Decision By",
    ]
    ws.append(headers)
    for r in qs:
        ws.append(
            [
                str(r.intake_timestamp),
                r.factory.code,
                r.tea_buying_center.code,
                r.supplier.code,
                r.batch.batch_code,
                r.effective_pluck_score(),
                float(r.moisture_pct),
                float(r.foreign_matter_pct),
                float(r.quality_score),
                r.quality_status,
                r.decision or "Pending",
                r.inspector.username,
                r.decision_by.username if r.decision_by else "",
            ]
        )
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    resp = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="lqis-report-{timezone.now().strftime("%Y-%m-%d_%H%M")}.xlsx"'
    return resp


def export_pdf(qs):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception:
        return export_csv(qs)

    output = BytesIO()
    p = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, height - 40, "LQIS Report Summary")
    p.setFont("Helvetica", 9)
    p.drawString(40, height - 56, f"Generated at: {timezone.now().strftime('%Y-%m-%d %H:%M')}")

    y = height - 80
    p.setFont("Helvetica-Bold", 8)
    p.drawString(40, y, "Time")
    p.drawString(120, y, "Factory")
    p.drawString(170, y, "Center")
    p.drawString(220, y, "Batch")
    p.drawString(280, y, "Quality")
    p.drawString(340, y, "Status")
    p.drawString(410, y, "Decision")
    y -= 14
    p.setFont("Helvetica", 8)

    for r in qs[:120]:
        if y < 50:
            p.showPage()
            y = height - 40
            p.setFont("Helvetica", 8)
        p.drawString(40, y, r.intake_timestamp.strftime("%Y-%m-%d %H:%M"))
        p.drawString(120, y, r.factory.code)
        p.drawString(170, y, r.tea_buying_center.code)
        p.drawString(220, y, r.batch.batch_code[:12])
        p.drawString(280, y, str(r.quality_score))
        p.drawString(340, y, r.quality_status)
        p.drawString(410, y, (r.decision or "Pending")[:18])
        y -= 12

    p.save()
    output.seek(0)
    resp = HttpResponse(output.read(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="lqis-report-{timezone.now().strftime("%Y-%m-%d_%H%M")}.pdf"'
    return resp
