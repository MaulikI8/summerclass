import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
application = get_wsgi_application()

# Ensure migrations and initial superuser exist when Gunicorn worker boots
try:
    from django.core.management import call_command
    call_command('migrate', interactive=False)
except Exception as e:
    print(f"[WSGI Init Notice]: {e}")
