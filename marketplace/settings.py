import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load local .env if present
env_file = BASE_DIR / '.env'
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-&!7=4y@z$eymqm#rhw6h1&%6=x*=q#=%49c$04j_w^=2iokbh8')
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
if '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.extend(['.onrender.com', 'localhost', '127.0.0.1'])

CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'http://127.0.0.1',
    'http://localhost',
]
rendered_url = os.environ.get('RENDER_EXTERNAL_URL')
if rendered_url:
    CSRF_TRUSTED_ORIGINS.append(rendered_url)

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'products.apps.ProductsConfig',
    'blog.apps.BlogConfig',
    'pages.apps.PagesConfig',
    'sitesetting.apps.SitesettingConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF, WSGI_APPLICATION = 'marketplace.urls', 'marketplace.wsgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'Templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'pages.context_processors.page_links',
        'sitesetting.context_processors.site_settings',
    ]},
}]

try:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
            conn_max_age=600
        )
    }
except ImportError:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_PASSWORD_VALIDATORS = [{'NAME': f'django.contrib.auth.password_validation.{v}'} for v in ['UserAttributeSimilarityValidator', 'MinimumLengthValidator', 'CommonPasswordValidator', 'NumericPasswordValidator']]

LANGUAGE_CODE, TIME_ZONE, USE_I18N, USE_TZ = 'en-us', 'UTC', True, True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "marketplace" / "static"]
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL, MEDIA_ROOT = '/media/', BASE_DIR / 'media'

EMAIL_MICROSERVICE_URL = os.environ.get('EMAIL_MICROSERVICE_URL', 'https://api.resend.com/emails')
EMAIL_MICROSERVICE_API_KEY = os.environ.get('EMAIL_MICROSERVICE_API_KEY', '')
EMAIL_SENDER_NAME, EMAIL_SENDER_ADDRESS = "Islington Marketplace", "onboarding@resend.dev"
EMAIL_MICROSERVICE_MOCK = os.environ.get('EMAIL_MICROSERVICE_MOCK', 'False').lower() in ('true', '1', 'yes')