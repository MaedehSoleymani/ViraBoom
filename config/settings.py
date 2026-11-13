"""
تنظیمات پروژه Viraboom (Django 5.x).

بخش‌هایی که مربوط به اپ accounts هستند با برچسب [ACCOUNTS] مشخص شده‌اند.
هم‌تیمی‌ها اپ‌های خودشان را فقط به INSTALLED_APPS اضافه می‌کنند.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    """فایل .env کنار manage.py را (بدون نیاز به پکیج اضافه) در os.environ می‌ریزد."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# ── Core ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
ADMIN_URL = os.environ.get("DJANGO_ADMIN_URL", "admin/")  # در پروداکشن عوضش کنید

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local apps
    "apps.accounts",  # [ACCOUNTS]
    # "apps.catalog",
    # "apps.cart",
    # "apps.orders",
    # "apps.downloads",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.site",  # [ACCOUNTS] SITE_NAME و ...
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ── [ACCOUNTS] احراز هویت ────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"          # ⚠️ باید قبل از اولین migrate ست شده باشد
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# اعتبار لینک «تأیید ایمیل» و «بازیابی رمز» (ثانیه) — ۲۴ ساعت
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14      # ۱۴ روز (وقتی «مرا به خاطر بسپار» فعال باشد)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# اطلاعات سایت (در base.html و ایمیل‌ها استفاده می‌شود)
SITE_NAME = "ویرابوم"
SITE_DESCRIPTION = "ویرابوم؛ فروشگاه قالب و طرح‌های گرافیکی آماده. قالب‌های حرفه‌ای را بخرید، دانلود کنید و در چند دقیقه شخصی‌سازی کنید."

# ایمیل: به‌طور پیش‌فرض (توسعه) ایمیل‌ها «داخل ترمینال» چاپ می‌شوند و واقعاً ارسال نمی‌شوند.
# برای ارسال واقعی، مقدارهای EMAIL_* را در فایل .env بگذارید (نمونه: .env.example).
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)  # پورت 465 (TLS و SSL را هم‌زمان فعال نکنید)
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))  # اگر SMTP در دسترس نبود، ثبت‌نام بیش از ۱۰ ثانیه گیر نکند
# آدرس فرستنده باید با حساب SMTP یکی باشد (مثلاً در جیمیل وگرنه بازنویسی می‌شود)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL") or (
    f"{SITE_NAME} <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else f"{SITE_NAME} <no-reply@viraboom.ir>"
)

# کش (برای محدودکردن تلاش‌های ناموفق ورود). در پروداکشن از Redis استفاده کنید.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# ── i18n ────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# ── Static & media ──────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── امنیت در پروداکشن ───────────────────────────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
