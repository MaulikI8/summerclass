import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
application = get_wsgi_application()

# Ensure migrations and initial superuser exist whenever Gunicorn boots
try:
    from django.core.management import call_command
    call_command('migrate', interactive=False)

    from django.contrib.auth.models import User
    user, created = User.objects.get_or_create(username='maulik', defaults={'email': 'maulikj663@gmail.com'})
    user.set_password('1234')
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    user.save()
    print(f"[WSGI Init]: Admin superuser 'maulik' is active.")
except Exception as e:
    print(f"[WSGI Init Notice]: {e}")
