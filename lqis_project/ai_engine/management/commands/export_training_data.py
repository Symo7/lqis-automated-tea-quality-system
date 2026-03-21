import csv
import sys
from django.core.management.base import BaseCommand
from sampling.models import FactoryIntakeSample

class Command(BaseCommand):
    help = "Export ground-truth AI labeled data for Machine Learning training pipelines."

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Optional destination CSV file path. Defaults to stdout.',
        )

    def handle(self, *args, **options):
        # Only pull images that human Reviewers have explicitly graded
        labeled_samples = FactoryIntakeSample.objects.filter(
            ai_label_grade__isnull=False
        ).exclude(leaf_image="").select_related("factory", "supplier")

        if not labeled_samples.exists():
            self.stdout.write(self.style.WARNING("No labeled ground-truth data found to export."))
            return

        out_path = options['output']
        file_handle = open(out_path, mode='w', newline='', encoding='utf-8') if out_path else sys.stdout

        try:
            writer = csv.writer(file_handle)
            # CNNs typically need: [image_path/url, label, metadata...]
            writer.writerow([
                "sample_id", 
                "image_url", 
                "label_grade", 
                "moisture_pct", 
                "factory_code", 
                "supplier_name", 
                "labeled_at"
            ])

            for sample in labeled_samples.iterator():
                writer.writerow([
                    sample.id,
                    sample.leaf_image.url,
                    sample.ai_label_grade,
                    sample.moisture_pct,
                    sample.factory.code,
                    sample.supplier.name,
                    sample.ai_label_timestamp.isoformat() if sample.ai_label_timestamp else ""
                ])

            if out_path:
                self.stdout.write(self.style.SUCCESS(f"Successfully exported {labeled_samples.count()} ground-truth rows to {out_path}"))
            
        finally:
            if out_path:
                file_handle.close()
