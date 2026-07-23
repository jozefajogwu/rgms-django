"""
Django settings for rgms_core project.
"""

import os
from pathlib import Path
from decouple import config
import dj_database_url
from dotenv import load_dotenv
load_dotenv()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING
SECRET_KEY = config('SECRET_KEY', default='django-insecure-w%@jjq5-c(-h4_k7_t2b2pm^i0#wih^#e!t9zkfljw)b6$77av')
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='127.0.0.1,localhost,remote-geriatric-monitoring-system.onrender.com'
).split(',')

# Application definition
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
# DATABASE CONFIGURATION - FIXED
# ============================================
# First, define DATABASES with SQLite as default
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Then, optionally override with PostgreSQL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Use PostgreSQL from DATABASE_URL
    DATABASES['default'] = dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
    print(f"✅ Using PostgreSQL database")
else:
    # If no DATABASE_URL, use SQLite (for local development)
    print("ℹ️ Using SQLite database (set DATABASE_URL for PostgreSQL)")

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

## rgms_core/settings.py

# ============================================
# JAZZMIN CONFIGURATION
# ============================================
JAZZMIN_SETTINGS = {
    "site_title": "Genesis Portal Admin",
    "site_header": "Genesis Portal",
    "site_brand": "Genesis Portal",
    "welcome_sign": "Welcome to Genesis Portal Admin",
    "copyright": "Genesis Portal © 2026",
    
    # ============================================
    # LOGO SETTINGS - TRY THESE OPTIONS
    # ============================================
    
    # Option 1: Try with leading slash (RECOMMENDED)
    "site_logo": "/static/admin/img/logo.png",
    "site_logo_classes": "img-fluid",  # Changed from img-circle
    "site_icon": "/static/admin/img/favicon.ico",
    "login_logo": "/static/admin/img/logo.png",
    "login_logo_classes": "img-fluid",
    
    # Option 2: If Option 1 doesn't work, try using images folder
    # "site_logo": "/static/images/logo.png",
    # "login_logo": "/static/images/logo.png",
    
    # Option 3: If Option 2 doesn't work, try without leading slash
    # "site_logo": "admin/img/logo.png",
    # "login_logo": "admin/img/logo.png",
    
    # Option 4: Try using STATIC_URL
    # "site_logo": "img/logo.png",
    # "login_logo": "img/logo.png",
    
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

# Email Configuration
# For testing (prints email to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'RGMS System <noreply@rgms.com>'

# Logout redirect URL
LOGOUT_REDIRECT_URL = 'home'  # Redirect to homepage after logout