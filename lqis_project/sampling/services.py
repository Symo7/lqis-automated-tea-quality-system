from __future__ import annotations

from decimal import Decimal

from core.models import FactoryThreshold
from sampling.models import FactoryIntakeSample, QualityAlert


def resolve_threshold(sample: FactoryIntakeSample) -> FactoryThreshold | None:
    return FactoryThreshold.objects.filter(factory=sample.factory).first()


def calculate_quality(sample: FactoryIntakeSample) -> tuple[Decimal, str]:
    effective_pluck = Decimal(sample.effective_pluck_score())
    moisture = Decimal(sample.moisture_pct)
    foreign = Decimal(sample.foreign_matter_pct)

    moisture_penalty = max(Decimal("0"), (moisture - Decimal("7.0")) * Decimal("3.5"))
    foreign_penalty = max(Decimal("0"), foreign * Decimal("8.0"))

    score = (effective_pluck * Decimal("0.70")) + (Decimal("30") - moisture_penalty - foreign_penalty)
    score = max(Decimal("0"), min(Decimal("100"), score))

    if score >= 85:
        status = "Excellent"
    elif score >= 70:
        status = "Acceptable"
    elif score >= 50:
        status = "Warning"
    else:
        status = "Reject"

    return score.quantize(Decimal("0.01")), status


def refresh_alerts(sample: FactoryIntakeSample) -> None:
    QualityAlert.objects.filter(sample=sample).delete()

    threshold = resolve_threshold(sample)
    min_pluck = threshold.min_pluck if threshold else 60
    max_moisture = Decimal(threshold.max_moisture) if threshold else Decimal("8.00")
    max_foreign = Decimal(threshold.max_foreign_matter) if threshold else Decimal("2.00")

    if sample.effective_pluck_score() < int(min_pluck):
        QualityAlert.objects.create(
            sample=sample,
            alert_type="LOW_PLUCK",
            message=f"Pluck score {sample.effective_pluck_score()} below threshold {min_pluck}",
        )

    if Decimal(sample.moisture_pct) > max_moisture:
        QualityAlert.objects.create(
            sample=sample,
            alert_type="HIGH_MOISTURE",
            message=f"Moisture {sample.moisture_pct}% above threshold {max_moisture}%",
        )

    if Decimal(sample.foreign_matter_pct) > max_foreign:
        QualityAlert.objects.create(
            sample=sample,
            alert_type="HIGH_FOREIGN",
            message=f"Foreign matter {sample.foreign_matter_pct}% above threshold {max_foreign}%",
        )
