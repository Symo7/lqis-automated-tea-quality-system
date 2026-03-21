import json
import os
from datetime import datetime

from django.core import serializers
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = "Exports all core, sampling, and user data to a timestamped JSON backup for testing/recovery."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Specific file path for the backup (default: backups/lqis_backup_TIMESTAMP.json)',
        )

    def handle(self, *args, **options):
        # Models to back up in order (dependencies first)
        MODELS_TO_BACKUP = [
            ('auth', 'User'),
            ('auth', 'Group'),
            ('core', 'Factory'),
            ('core', 'TeaBuyingCenter'),
            ('core', 'Supplier'),
            ('core', 'Batch'),
            ('core', 'FactoryThreshold'),
            ('sampling', 'FactoryIntakeSample'),
            ('sampling', 'SampleDecisionHistory'),
        ]

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        output_path = options['file'] or os.path.join(backup_dir, f"lqis_backup_{timestamp}.json")

        self.stdout.write(f"Starting backup to {output_path}...")

        all_objects = []
        for app_label, model_name in MODELS_TO_BACKUP:
            model = apps.get_model(app_label, model_name)
            all_objects.extend(list(model.objects.all()))

        try:
            data = serializers.serialize("json", all_objects, indent=2)
            with open(output_path, "w") as f:
                f.write(data)
            self.stdout.write(self.style.SUCCESS(f"Successfully backed up {len(all_objects)} objects to {output_path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Backup failed: {str(e)}"))
