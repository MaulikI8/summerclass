import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

env_file = BASE_DIR / '.env'
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-&!7=4y@z$eymqm#rhw6h1&%6=x*=q#=%49c$04j_w^=2iokbh8')
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
if '*' not in ALLOWED_HOSTS: ALLOWED_HOSTS.extend(['.onrender.com', 'localhost', '127.0.0.1'])

CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com', 'https://maulikjoshi.com.np', 'https://*.maulikjoshi.com.np', 'http://127.0.0.1', 'http://localhost']
if os.environ.get('RENDER_EXTERNAL_URL'): CSRF_TRUSTED_ORIGINS.append(os.environ.get('RENDER_EXTERNAL_URL'))

try:
    import cloudinary_storage
    HAS_CLOUDINARY = True
except ImportError:
    HAS_CLOUDINARY = False

INSTALLED_APPS = [
    'jazzmin', 'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages',
    'whitenoise.runserver_nostatic', 'django.contrib.staticfiles',
]
if HAS_CLOUDINARY:
    INSTALLED_APPS.extend(['cloudinary_storage', 'cloudinary'])
INSTALLED_APPS.extend([
    'account.apps.AccountConfig', 'cart.apps.CartConfig', 'products.apps.ProductsConfig', 'blog.apps.BlogConfig', 'pages.apps.PagesConfig', 'sitesetting.apps.SitesettingConfig',
])

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF, WSGI_APPLICATION = 'marketplace.urls', 'marketplace.wsgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'Templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages', 'pages.context_processors.page_links',
        'sitesetting.context_processors.site_settings', 'cart.context_processors.cart_counter',
    ]},
}]

try:
    import dj_database_url
    DATABASES = {'default': dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=600)}
except ImportError:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_PASSWORD_VALIDATORS = [{'NAME': f'django.contrib.auth.password_validation.{v}'} for v in ['UserAttributeSimilarityValidator', 'MinimumLengthValidator', 'CommonPasswordValidator', 'NumericPasswordValidator']]
LANGUAGE_CODE, TIME_ZONE, USE_I18N, USE_TZ = 'en-us', 'UTC', True, True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL, STATICFILES_DIRS, STATIC_ROOT = '/static/', [BASE_DIR / "marketplace" / "static"], BASE_DIR / 'staticfiles'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', 'vktqosuy'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', '297815742518524'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', 'vNS2RE1uaxLIwl36s-SeRBpx1ng'),
}
if HAS_CLOUDINARY:
    STORAGES = {
        "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }
WHITENOISE_USE_FINDERS, WHITENOISE_AUTOREFRESH = True, True

MEDIA_URL = '/media/'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 465))
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'True').lower() in ('true', '1', 'yes')
EMAIL_USE_TLS = False
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'maulikj663@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'lwdtdidnicnudkxr')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', f"Islington Marketplace <{EMAIL_HOST_USER}>")
EMAIL_SENDER_NAME = os.environ.get('EMAIL_SENDER_NAME', 'Islington Marketplace')

# --- Khalti Payment Gateway Settings ---
# Configured via environment variable KHALTI_SECRET_KEY in Render Dashboard
KHALTI_SECRET_KEY = os.environ.get('KHALTI_SECRET_KEY', '')
KHALTI_INITIATE_URL = os.environ.get('KHALTI_INITIATE_URL', 'https://dev.khalti.com/api/v2/epayment/initiate/')
KHALTI_LOOKUP_URL = os.environ.get('KHALTI_LOOKUP_URL', 'https://dev.khalti.com/api/v2/epayment/lookup/')