import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
application = get_wsgi_application()

# Ensure migrations and initial superuser exist via environment variables
try:
    from django.core.management import call_command
    call_command('migrate', interactive=False)

    admin_username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'maulik')
    admin_email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'maulikj663@gmail.com')
    admin_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '1234')

    from django.contrib.auth.models import User
    user, created = User.objects.get_or_create(username=admin_username, defaults={'email': admin_email})
    if created:
        user.set_password(admin_password)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save()
        print(f"[WSGI Init]: Created superuser '{admin_username}' from environment settings.")
    elif not user.is_superuser or not user.is_staff:
        user.is_superuser = True
        user.is_staff = True
        user.save()
except Exception as e:
    print(f"[WSGI Init Notice]: {e}")
