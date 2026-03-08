"""WSGI config for lqis_project."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lqis_project.settings')

application = get_wsgi_application()
