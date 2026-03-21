import datetime

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Q
from django.urls import reverse
from django.utils import timezone

from sampling.models import FactoryIntakeSample


class Command(BaseCommand):
    help = "Generates and emails a weekly quality report to all supervisors."

    def handle(self, *args, **options):
        now = timezone.now()
        seven_days_ago = now - datetime.timedelta(days=7)

        samples = FactoryIntakeSample.objects.filter(
            intake_timestamp__gte=seven_days_ago,
            intake_timestamp__lte=now
        )

        total_samples = samples.count()
        if total_samples == 0:
            self.stdout.write(self.style.WARNING("No samples collected in the last 7 days. Skip emailing."))
            return

        avg_quality = samples.aggregate(avg=Avg("quality_score"))["avg"] or 0
        rejects = samples.filter(quality_status="Reject").count()
        reject_pct = (rejects / total_samples * 100) if total_samples else 0

        pending_decisions = samples.filter(decision="").count()

        # Find all Supervisors
        supervisor_group = Group.objects.filter(name="Supervisor").first()
        if not supervisor_group:
            self.stdout.write(self.style.ERROR("Supervisor group does not exist!"))
            return

        supervisors = supervisor_group.user_set.filter(is_active=True).exclude(email="")
        recipient_list = [user.email for user in supervisors]

        if not recipient_list:
            self.stdout.write(self.style.WARNING("No active supervisors with email addresses found."))
            return

        subject = f"LQIS Weekly Operations Summary ({seven_days_ago.date()} to {now.date()})"
        
        message = (
            f"Hello Supervisor,\n\n"
            f"Here is your weekly summary of tea intake operations for the past 7 days:\n\n"
            f"• Total Samples Intaken: {total_samples}\n"
            f"• Average Quality Score: {avg_quality:.1f} / 100\n"
            f"• Rejected Samples: {rejects} ({reject_pct:.1f}%)\n"
            f"• Pending Decisions: {pending_decisions}\n\n"
            f"Please log in to the LQIS Dashboard to review pending batches and detailed alerts.\n"
            f"Thank you,\n"
            f"LQIS Automated System"
        )

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully sent weekly report to {len(recipient_list)} supervisors."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send email: {e}"))
