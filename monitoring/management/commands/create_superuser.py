# monitoring/management/commands/create_superuser.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    help = 'Create a superuser if none exists (for Render deployment)'

    def handle(self, *args, **options):
        # Get credentials from environment variables (SAFE)
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not User.objects.filter(username=username).exists():
            if password:
                # Create superuser with the password from environment
                User.objects.create_superuser(username, email, password)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Superuser "{username}" created successfully!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ DJANGO_SUPERUSER_PASSWORD environment variable is not set!')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Superuser "{username}" already exists.')
            )