import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from .utils import mask_phone, normalize_phone
from .validators import validate_image_size, validate_iranian_mobile


class Role(models.TextChoices):
    CUSTOMER = "customer", "خریدار"
    CREATOR = "creator", "طراح"
    SUPPORT = "support", "پشتیبان"
    ADMIN = "admin", "مدیر"


# نقش‌هایی که به پنل مدیریت (is_staff) دسترسی دارند
STAFF_ROLES = {Role.SUPPORT, Role.ADMIN}


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, password, **extra):
        if not phone:
            raise ValueError("شماره موبایل الزامی است.")
        phone = normalize_phone(phone)
        if extra.get("email"):
            extra["email"] = self.normalize_email(extra["email"]).lower()
        user = self.model(phone=phone, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra):
        extra.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra)

    def create_superuser(self, phone, password=None, **extra):
        extra["is_superuser"] = True
        extra["role"] = Role.ADMIN
        extra.setdefault("email_verified", True)
        return self._create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """کاربر سفارشی: شناسهٔ ورود = شماره موبایل."""

    phone = models.CharField(
        "شماره موبایل",
        max_length=11,
        unique=True,
        validators=[validate_iranian_mobile],
        error_messages={"unique": "کاربری با این شماره موبایل قبلاً ثبت‌نام کرده است."},
    )
    email = models.EmailField(
        "ایمیل",
        unique=True,
        null=True,
        blank=True,
        error_messages={"unique": "این ایمیل قبلاً برای حساب دیگری ثبت شده است."},
    )
    first_name = models.CharField("نام", max_length=60, blank=True)
    last_name = models.CharField("نام خانوادگی", max_length=60, blank=True)
    role = models.CharField("نقش", max_length=20, choices=Role.choices, default=Role.CUSTOMER, db_index=True)

    is_active = models.BooleanField("فعال", default=True)
    is_staff = models.BooleanField("دسترسی به پنل ادمین جنگو", default=False, editable=False)
    email_verified = models.BooleanField("ایمیل تأیید شده", default=False)
    email_verified_at = models.DateTimeField("زمان تأیید ایمیل", null=True, blank=True)
    date_joined = models.DateTimeField("تاریخ عضویت", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        self.email = (self.email or "").strip().lower() or None
        # is_staff همیشه از روی نقش محاسبه می‌شود (تنها منبع حقیقت = role)
        self.is_staff = bool(self.is_superuser or self.role in STAFF_ROLES)
        super().save(*args, **kwargs)

    # ── نام‌ها ──
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.display_name

    @property
    def display_name(self):
        return self.get_full_name() or self.masked_phone

    @property
    def masked_phone(self):
        return mask_phone(self.phone)

    # ── نقش‌ها ──
    @property
    def can_manage_users(self):
        return self.is_superuser or self.role == Role.ADMIN

    def has_role(self, *roles):
        return self.is_superuser or self.role in roles

    def mark_email_verified(self):
        self.email_verified = True
        self.email_verified_at = timezone.now()
        self.save(update_fields=["email_verified", "email_verified_at"])


def avatar_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"avatars/user_{instance.user_id}/{uuid.uuid4().hex}.{ext}"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(
        "تصویر پروفایل",
        upload_to=avatar_upload_path,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validate_image_size],
    )
    bio = models.TextField("دربارهٔ من", max_length=500, blank=True)
    city = models.CharField("شهر", max_length=60, blank=True)
    website = models.URLField("وب‌سایت", blank=True)
    instagram = models.CharField("اینستاگرام", max_length=30, blank=True, help_text="بدون @")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "پروفایل"
        verbose_name_plural = "پروفایل‌ها"

    def __str__(self):
        return f"پروفایل {self.user.display_name}"

    @property
    def completion_percent(self):
        u = self.user
        checks = [
            bool(u.first_name),
            bool(u.last_name),
            u.email_verified,
            bool(self.avatar),
            bool(self.bio),
            bool(self.city),
        ]
        return round(100 * sum(checks) / len(checks))
