"""
Django settings for rgms_core project.
"""

import os
from pathlib import Path
from decouple import config
import dj_database_url
from dotenv import load_dotenv

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================
# LOAD .ENV FILE - Explicitly from project root
# ============================================
env_path = BASE_DIR / '.env'
print(f"🔍 Loading .env from: {env_path}")
print(f"🔍 .env exists: {env_path.exists()}")
load_dotenv(dotenv_path=env_path, override=True)

# ============================================
# SECURITY WARNING
# ============================================
SECRET_KEY = config('SECRET_KEY', default='django-insecure-w%@jjq5-c(-h4_k7_t2b2pm^i0#wih^#e!t9zkfljw)b6$77av')
DEBUG = config('DEBUG', default=False, cast=bool)

# ============================================
# ALLOWED HOSTS
# ============================================
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='127.0.0.1,localhost,remotehealthmonitor.com.ng,www.remotehealthmonitor.com.ng'
).split(',')

# ============================================
# CSRF TRUSTED ORIGINS
# ============================================
CSRF_TRUSTED_ORIGINS = [
    'https://remotehealthmonitor.com.ng',
    'https://www.remotehealthmonitor.com.ng',
    'http://remotehealthmonitor.com.ng',
    'http://www.remotehealthmonitor.com.ng',
]

# ============================================
# DATABASE CONFIGURATION
# ============================================
DATABASE_URL = os.environ.get('DATABASE_URL')
print(f"🔍 DEBUG: DATABASE_URL = {DATABASE_URL}")

if DATABASE_URL and DATABASE_URL.startswith('postgres'):
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    print("✅ Using PostgreSQL database")
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    print("⚠️ Falling back to SQLite (DATABASE_URL not set or invalid)")

# ============================================
# APPLICATION DEFINITION
# ============================================
INSTALLED_APPS = [
    'jazzmin',  # MUST BE FIRST
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'monitoring',
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

ROOT_URLCONF = 'rgms_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'rgms_core.wsgi.application'

# ============================================
# PASSWORD VALIDATION
# ============================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ============================================
# INTERNATIONALIZATION
# ============================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ============================================
# STATIC FILES
# ============================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================
# MEDIA FILES
# ============================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ============================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================
# SECURITY SETTINGS - Enable once SSL is working
# ============================================
# Uncomment these after SSL is set up:
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# X_FRAME_OPTIONS = 'DENY'
# SECURE_HSTS_SECONDS = 31536000  # 1 year
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# ============================================
# JAZZMIN CONFIGURATION
# ============================================
JAZZMIN_SETTINGS = {
    "site_title": "RHMS Admin",
    "site_header": "Remote Health Monitoring System",
    "site_brand": "RHMS",
    "welcome_sign": "Welcome to RHMS Admin",
    "copyright": "RHMS © 2026",
    
    # Logo Settings
    "site_logo": "images/logo.png",
    "site_logo_classes": "img-fluid",
    "site_icon": "/static/admin/img/favicon.ico",
    "login_logo": "images/logo.png",
    "login_logo_classes": "img-fluid",
    
    "show_sidebar": True,
    "navigation_expanded": True,
    "navigation": [
        {
            "name": "Monitoring",
            "icon": "fas fa-heartbeat",
            "children": [
                {
                    "name": "Patients",
                    "url": "/admin/monitoring/patient/",
                    "icon": "fas fa-user-injured"
                },
                {
                    "name": "Vital Readings",
                    "url": "/admin/monitoring/vitalreading/",
                    "icon": "fas fa-heartbeat"
                },
                {
                    "name": "Alerts",
                    "url": "/admin/monitoring/alert/",
                    "icon": "fas fa-bell"
                },
            ]
        },
        {
            "name": "User Management",
            "icon": "fas fa-users-cog",
            "children": [
                {
                    "name": "Users",
                    "url": "/admin/auth/user/",
                    "icon": "fas fa-user"
                },
                {
                    "name": "Groups",
                    "url": "/admin/auth/group/",
                    "icon": "fas fa-users"
                },
            ]
        }
    ]
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    }
}

# ============================================
# EMAIL CONFIGURATION
# ============================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('GMAIL_EMAIL')
EMAIL_HOST_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
DEFAULT_FROM_EMAIL = f'RGMS System <{os.getenv("GMAIL_EMAIL")}>'

# ============================================
# URL CONFIGURATION
# ============================================
SITE_URL = 'https://remotehealthmonitor.com.ng'
BASE_URL = SITE_URL

# ============================================
# AUTHENTICATION & LOGIN
# ============================================
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/caregiver/dashboard/'

# ============================================
# LOGGING (Optional - for debugging)
# ============================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'monitoring': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}