import os

from django.core import serializers
from django.core.management.base import BaseCommand
from django.db import transaction

class Command(BaseCommand):
    help = "Restores database state from a JSON backup file. CAUTION: Destructive operation."

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            type=str,
            help='Path to the JSON backup file to restore from.',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Bypasses confirmation prompt.',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f"Backup file {file_path} not found."))
            return

        if not options['confirm']:
            confirm = input(f"This will DESTROY existing data and restore from {file_path}. Type 'RESTORE' to proceed: ")
            if confirm != 'RESTORE':
                self.stdout.write("Operation cancelled.")
                return

        self.stdout.write(f"Commencing restore from {file_path}...")

        try:
            with open(file_path, "r") as f:
                data = f.read()
            
            # Using transaction to ensure atomic restore
            with transaction.atomic():
                # We deserialize and save. Django handles generic JSON deserialization.
                # Note: loaddata management command is another option, but custom script
                # gives us more granular control over atomic transactions and confirmation.
                for obj in serializers.deserialize("json", data):
                    obj.save()
                    
            self.stdout.write(self.style.SUCCESS(f"Successfully restored database from {file_path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Restore failed: {str(e)}"))
