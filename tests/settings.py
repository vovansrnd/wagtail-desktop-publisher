"""Изолированные Django-настройки для регрессионных тестов wagtail_api.

SQLite in-memory, тестовая БД создаётся/удаляется DiscoverRunner'ом.
Никаких production/staging подключений и внешних сетевых обращений.
"""
SECRET_KEY = "wdp-test-only-not-a-production-secret"
DEBUG = True
USE_TZ = True
import tempfile

STATIC_URL = "/static/"
MEDIA_ROOT = tempfile.mkdtemp(prefix="wdp-test-media-")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "taggit",
    "modelcluster",
    "wagtail",
    "wagtail.images",
    "wagtail.admin",
    "wagtail.documents",
    "wagtail.users",
    "wagtail.sites",
    "wagtail.snippets",
    "wagtail.contrib.forms",
    "wagtail.search",
    "wagtail.embeds",
    "wagtail.contrib.redirects",
    "wagtail_desktop_publisher",
]
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WAGTAIL_SITE_NAME = "test"
WAGTAILADMIN_BASE_URL = "http://tests.local"
ROOT_URLCONF = "tests.urls"
