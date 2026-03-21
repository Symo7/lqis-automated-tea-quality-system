from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Batch, Factory, FactoryThreshold, Supplier, TeaBuyingCenter
from sampling.models import FactoryIntakeSample
from sampling.services import calculate_quality, refresh_alerts


class Command(BaseCommand):
    help = "Seed demo users, roles, and Phase 2 baseline data."

    def handle(self, *args, **options):
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        inspector_group, _ = Group.objects.get_or_create(name="Inspector")
        supervisor_group, _ = Group.objects.get_or_create(name="Supervisor")
        manager_group, _ = Group.objects.get_or_create(name="Factory Manager")

        admin, _ = User.objects.get_or_create(username="admin", defaults={"is_staff": True, "is_superuser": True})
        admin.set_password("admin123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        admin.groups.add(admin_group)

        inspector, _ = User.objects.get_or_create(username="inspector1")
        inspector.set_password("admin123")
        inspector.save()
        inspector.groups.add(inspector_group)

        supervisor, _ = User.objects.get_or_create(username="supervisor1")
        supervisor.set_password("admin123")
        supervisor.save()
        supervisor.groups.add(supervisor_group)

        manager, _ = User.objects.get_or_create(username="manager1")
        manager.set_password("admin123")
        manager.save()
        manager.groups.add(manager_group)

        f1, _ = Factory.objects.get_or_create(code="F001", defaults={"name": "Kericho Main", "location": "Kericho"})
        f2, _ = Factory.objects.get_or_create(code="F002", defaults={"name": "Nandi Intake", "location": "Nandi"})

        c1, _ = TeaBuyingCenter.objects.get_or_create(factory=f1, code="BC101", defaults={"name": "Kapsoit Center"})
        c2, _ = TeaBuyingCenter.objects.get_or_create(factory=f1, code="BC102", defaults={"name": "Ainamoi Center"})
        c3, _ = TeaBuyingCenter.objects.get_or_create(factory=f2, code="BC201", defaults={"name": "Kapsabet Center"})

        s1, _ = Supplier.objects.get_or_create(code="SUP001", defaults={"name": "Green Valley Farmers", "is_farmer_group": True})
        s2, _ = Supplier.objects.get_or_create(code="SUP002", defaults={"name": "Highland Leaf Ltd", "is_farmer_group": False})

        b1, _ = Batch.objects.get_or_create(
            batch_code="BATCH-2026-001",
            defaults={"factory": f1, "buying_center": c1, "supplier": s1, "intake_date": timezone.localdate()},
        )
        b2, _ = Batch.objects.get_or_create(
            batch_code="BATCH-2026-002",
            defaults={"factory": f1, "buying_center": c2, "supplier": s2, "intake_date": timezone.localdate()},
        )
        b3, _ = Batch.objects.get_or_create(
            batch_code="BATCH-2026-003",
            defaults={"factory": f2, "buying_center": c3, "supplier": s1, "intake_date": timezone.localdate()},
        )

        FactoryThreshold.objects.update_or_create(factory=f1, defaults={"min_pluck": 65, "max_moisture": Decimal("8.00"), "max_foreign_matter": Decimal("2.00")})
        FactoryThreshold.objects.update_or_create(factory=f2, defaults={"min_pluck": 60, "max_moisture": Decimal("8.50"), "max_foreign_matter": Decimal("2.50")})

        now = timezone.now()
        for i, (factory, center, supplier, batch, pluck, moist, foreign) in enumerate(
            [
                (f1, c1, s1, b1, 82, Decimal("7.20"), Decimal("1.10")),
                (f1, c2, s2, b2, 58, Decimal("8.90"), Decimal("2.20")),
                (f2, c3, s1, b3, 68, Decimal("7.80"), Decimal("1.90")),
            ]
        ):
            sample, _ = FactoryIntakeSample.objects.get_or_create(
                batch=batch,
                intake_timestamp=now - timedelta(hours=i * 3),
                defaults={
                    "factory": factory,
                    "tea_buying_center": center,
                    "supplier": supplier,
                    "inspector": inspector,
                    "leaf_image": "",
                    "predicted_pluck_class": "Good",
                    "predicted_pluck_score": pluck,
                    "prediction_confidence": Decimal("75.00"),
                    "moisture_pct": moist,
                    "foreign_matter_pct": foreign,
                    "notes": "Seed sample",
                },
            )
            score, status = calculate_quality(sample)
            sample.quality_score = score
            sample.quality_status = status
            sample.save(update_fields=["quality_score", "quality_status", "updated_at"])
            refresh_alerts(sample)

        self.stdout.write(self.style.SUCCESS("Demo users, roles, and sample data seeded."))
