import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')

# Automatically apply database migrations on Gunicorn boot
try:
    import django
    django.setup()
    from django.core.management import call_command
    call_command('migrate', interactive=False)
except Exception as e:
    print(f"[WSGI Startup Migrate Info]: {e}")

application = get_wsgi_application()
