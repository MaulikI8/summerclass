import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')

# Automatically apply database migrations on Gunicorn boot
try:
    import django
    django.setup()
    from django.core.management import call_command
    call_command('migrate', interactive=False)

    from sitesetting.storage import sync_local_media_to_db
    sync_local_media_to_db()
except Exception as e:
    print(f"[WSGI Startup Migrate/Sync Info]: {e}")

application = get_wsgi_application()
