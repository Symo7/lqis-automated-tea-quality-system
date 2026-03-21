from django.core.exceptions import ValidationError
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Factory(TimeStampedModel):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True)
    location = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class TeaBuyingCenter(TimeStampedModel):
    factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name="buying_centers")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20)
    location = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("factory", "code")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} - {self.factory.code}"


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, unique=True)
    contact = models.CharField(max_length=120, blank=True)
    is_farmer_group = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Batch(TimeStampedModel):
    factory = models.ForeignKey(Factory, on_delete=models.PROTECT, related_name="batches")
    buying_center = models.ForeignKey(TeaBuyingCenter, on_delete=models.PROTECT, related_name="batches")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="batches")
    batch_code = models.CharField(max_length=50, unique=True)
    intake_date = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-intake_date", "batch_code"]

    def clean(self) -> None:
        if self.buying_center_id and self.factory_id and self.buying_center.factory_id != self.factory_id:
            raise ValidationError("Buying center must belong to selected factory.")

    def __str__(self) -> str:
        return self.batch_code


class FactoryThreshold(TimeStampedModel):
    factory = models.OneToOneField(Factory, on_delete=models.CASCADE, related_name="threshold")
    min_pluck = models.PositiveIntegerField(default=60)
    max_moisture = models.DecimalField(max_digits=5, decimal_places=2, default=8.00)
    max_foreign_matter = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)

    def __str__(self) -> str:
        return f"Thresholds: {self.factory.code}"


class AuditLog(models.Model):
    """
    Immutable record of every significant user action for KTDA accountability.
    Once written, audit logs should NEVER be modified or deleted.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('EXPORT', 'Export'),
        ('DECISION', 'Decision'),
        ('SYNC', 'Sync'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_model = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=50, blank=True)
    detail = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.user} → {self.action} {self.target_model}#{self.target_id}"
