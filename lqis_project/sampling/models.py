from decimal import Decimal

from django.conf import settings
from django.db import models

from ai_engine.services import run_baseline_prediction
from core.models import Batch, Factory, Supplier, TeaBuyingCenter


class FactoryIntakeSample(models.Model):
    PLUCK_CLASSES = [
        ("Excellent", "Excellent"),
        ("Good", "Good"),
        ("Fair", "Fair"),
        ("Poor", "Poor"),
    ]
    QUALITY_STATUS = [
        ("Excellent", "Excellent"),
        ("Acceptable", "Acceptable"),
        ("Warning", "Warning"),
        ("Reject", "Reject"),
    ]
    DECISIONS = [
        ("Approve Batch", "Approve Batch"),
        ("Reject Batch", "Reject Batch"),
        ("Send for Re-sorting", "Send for Re-sorting"),
        ("Hold for Review", "Hold for Review"),
    ]

    factory = models.ForeignKey(Factory, on_delete=models.PROTECT, related_name="samples")
    tea_buying_center = models.ForeignKey(TeaBuyingCenter, on_delete=models.PROTECT, related_name="samples")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="samples")
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name="samples")
    intake_timestamp = models.DateTimeField()
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inspected_samples")
    leaf_image = models.ImageField(upload_to="samples/")
    client_submission_id = models.CharField(max_length=64, blank=True, null=True, unique=True)

    predicted_pluck_class = models.CharField(max_length=20, choices=PLUCK_CLASSES)
    predicted_pluck_score = models.PositiveIntegerField(default=0)
    prediction_confidence = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    manual_override_pluck_score = models.PositiveIntegerField(null=True, blank=True)

    moisture_pct = models.DecimalField(max_digits=5, decimal_places=2)
    foreign_matter_pct = models.DecimalField(max_digits=5, decimal_places=2)
    notes = models.TextField(blank=True)

    quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    quality_status = models.CharField(max_length=20, choices=QUALITY_STATUS, default="Warning")

    decision = models.CharField(max_length=30, choices=DECISIONS, blank=True)
    decision_reason = models.TextField(blank=True)
    decision_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_samples",
    )
    decision_at = models.DateTimeField(null=True, blank=True)

    # AI Data Collection Fields (Ground Truth Generation)
    AI_LABELS = [
        ("Good", "Good"),
        ("Average", "Average"),
        ("Poor", "Poor"),
    ]
    ai_label_grade = models.CharField(max_length=20, choices=AI_LABELS, blank=True, null=True)
    ai_label_reason = models.TextField(blank=True)
    ai_label_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="labeled_ai_samples"
    )
    ai_label_timestamp = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-intake_timestamp"]

    def effective_pluck_score(self) -> int:
        return int(self.manual_override_pluck_score or self.predicted_pluck_score)

    def __str__(self) -> str:
        return f"{self.batch.batch_code} @ {self.intake_timestamp:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        if self.leaf_image and (not self.predicted_pluck_score or not self.predicted_pluck_class):
            prediction = run_baseline_prediction(self.leaf_image)
            self.predicted_pluck_class = prediction["predicted_pluck_class"]
            self.predicted_pluck_score = prediction["predicted_pluck_score"]
            self.prediction_confidence = Decimal(str(prediction["confidence"]))
        super().save(*args, **kwargs)


class QualityAlert(models.Model):
    ALERT_TYPES = [
        ("LOW_PLUCK", "LOW_PLUCK"),
        ("HIGH_MOISTURE", "HIGH_MOISTURE"),
        ("HIGH_FOREIGN", "HIGH_FOREIGN"),
    ]

    sample = models.ForeignKey(FactoryIntakeSample, on_delete=models.CASCADE, related_name="alerts")
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.alert_type}: {self.sample_id}"


class SampleDecisionHistory(models.Model):
    sample = models.ForeignKey(FactoryIntakeSample, on_delete=models.CASCADE, related_name="decision_history")
    decision = models.CharField(max_length=30, choices=FactoryIntakeSample.DECISIONS)
    reason = models.TextField(blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-decided_at"]

    def __str__(self) -> str:
        return f"{self.sample_id} - {self.decision}"
