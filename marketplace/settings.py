import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-&!7=4y@z$eymqm#rhw6h1&%6=x*=q#=%49c$04j_w^=2iokbh8'
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'products.apps.ProductsConfig',
    'blog.apps.BlogConfig',
    'pages.apps.PagesConfig',
    'sitesetting.apps.SitesettingConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'marketplace.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'Templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'pages.context_processors.page_links',
            'sitesetting.context_processors.site_settings',
        ],
    },
}]

WSGI_APPLICATION = 'marketplace.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE, TIME_ZONE, USE_I18N, USE_TZ = 'en-us', 'UTC', True, True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "marketplace" / "static"]
MEDIA_URL, MEDIA_ROOT = '/media/', BASE_DIR / 'media'

# Email Microservice
EMAIL_MICROSERVICE_URL = os.environ.get('EMAIL_MICROSERVICE_URL', 'https://api.resend.com/emails')
EMAIL_MICROSERVICE_API_KEY = os.environ.get('EMAIL_MICROSERVICE_API_KEY', '')
EMAIL_SENDER_NAME = "Islington Marketplace"
EMAIL_SENDER_ADDRESS = "onboarding@resend.dev"
EMAIL_MICROSERVICE_MOCK = os.environ.get('EMAIL_MICROSERVICE_MOCK', 'True').lower() in ('true', '1', 'yes')