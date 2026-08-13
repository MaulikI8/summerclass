#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Seed superuser using environment variables if configured
python manage.py shell -c "
import os
from django.contrib.auth.models import User

username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'maulik')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'maulikj663@gmail.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '1234')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'Superuser {username} created successfully.')
"
