#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Automatically ensure superuser exists for admin panel access
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='maulik').exists():
    User.objects.create_superuser('maulik', 'maulikj663@gmail.com', '1234')
    print('Superuser maulik created successfully.')
else:
    u = User.objects.get(username='maulik')
    u.set_password('1234')
    u.is_superuser = True
    u.is_staff = True
    u.save()
    print('Superuser maulik updated.')
"
