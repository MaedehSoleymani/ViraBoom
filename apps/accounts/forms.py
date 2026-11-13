import re

from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from . import throttle
from .models import Profile, Role, User
from .utils import get_client_ip, normalize_phone
from .validators import validate_iranian_mobile


# ─────────────────────────── ابزارهای مشترک ───────────────────────────
class StyledFormMixin:
    """کلاس‌های CSS را روی ویجت‌ها می‌گذارد و فیلدهای خطادار را aria-invalid می‌کند."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "check-input"
            elif isinstance(widget, forms.FileInput):
                css = "file-input"
            else:
                css = "input"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def full_clean(self):
        super().full_clean()
        for name in self._errors or {}:
            if name in self.fields:
                self.fields[name].widget.attrs["aria-invalid"] = "true"


class PhoneField(forms.CharField):
    """فیلد شمارهٔ موبایل: ارقام فارسی/+98 را نرمال می‌کند و قالب 09xxxxxxxxx را چک می‌کند."""

    default_validators = [validate_iranian_mobile]

    def __init__(self, **kwargs):
        kwargs.setdefault("label", "شماره موبایل")
        kwargs.setdefault("max_length", 20)
        kwargs.setdefault(
            "widget",
            forms.TextInput(
                attrs={
                    "inputmode": "tel",
                    "autocomplete": "tel",
                    "placeholder": "09123456789",
                    "dir": "ltr",
                    "data-phone": "",
                }
            ),
        )
        super().__init__(**kwargs)

    def to_python(self, value):
        return normalize_phone(super().to_python(value))


def _password_field(label, autocomplete, with_help=False):
    return forms.CharField(
        label=label,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": autocomplete, "dir": "ltr"}),
        help_text=password_validation.password_validators_help_text_html() if with_help else "",
    )


# ─────────────────────────── ثبت‌نام ───────────────────────────
class RegisterForm(StyledFormMixin, forms.ModelForm):
    phone = PhoneField()
    email = forms.EmailField(
        label="ایمیل",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "dir": "ltr", "placeholder": "name@example.com"}),
        help_text="لینک تأیید حساب و بازیابی رمز عبور به این ایمیل ارسال می‌شود.",
    )
    password1 = _password_field("رمز عبور", "new-password", with_help=True)
    password2 = _password_field("تکرار رمز عبور", "new-password")
    accept_terms = forms.BooleanField(
        label="قوانین و مقررات را می‌پذیرم",
        error_messages={"required": "برای ثبت‌نام باید قوانین را بپذیرید."},
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["first_name"].widget.attrs.update({"autocomplete": "given-name", "autofocus": True})
        self.fields["last_name"].widget.attrs.update({"autocomplete": "family-name"})

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "رمز عبور و تکرار آن یکسان نیستند.")
        elif p1:
            candidate = User(
                phone=cleaned.get("phone", ""),
                email=cleaned.get("email"),
                first_name=cleaned.get("first_name", ""),
                last_name=cleaned.get("last_name", ""),
            )
            try:
                password_validation.validate_password(p1, candidate)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = Role.CUSTOMER  # نقش را هرگز از ورودی کاربر نمی‌گیریم
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


# ─────────────────────────── ورود ───────────────────────────
class LoginForm(StyledFormMixin, forms.Form):
    phone = PhoneField()
    password = forms.CharField(
        label="رمز عبور",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "dir": "ltr"}),
    )
    remember_me = forms.BooleanField(label="مرا به خاطر بسپار", required=False)

    error_invalid = "شماره موبایل یا رمز عبور اشتباه است."
    error_locked = "تعداد تلاش‌های ناموفق زیاد بوده است. لطفاً ۱۵ دقیقه بعد دوباره تلاش کنید."

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)
        self.fields["phone"].widget.attrs.update({"autocomplete": "username", "autofocus": True})

    def clean(self):
        cleaned = super().clean()
        phone, password = cleaned.get("phone"), cleaned.get("password")
        if not phone or not password:
            return cleaned
        ip = get_client_ip(self.request)
        if throttle.is_locked(phone, ip):
            raise ValidationError(self.error_locked, code="locked")
        user = authenticate(self.request, username=phone, password=password)
        if user is None:
            throttle.register_failure(phone, ip)
            raise ValidationError(self.error_invalid, code="invalid_login")
        throttle.reset_failures(phone, ip)
        self.user = user
        return cleaned


# ─────────────────────────── پروفایل ───────────────────────────
class ProfileUserForm(StyledFormMixin, forms.ModelForm):
    email = forms.EmailField(
        label="ایمیل",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "dir": "ltr"}),
        help_text="با تغییر ایمیل، باید دوباره آن را تأیید کنید.",
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class ProfileDetailsForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("avatar", "bio", "city", "website", "instagram")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4, "maxlength": 500}),
            "website": forms.URLInput(attrs={"dir": "ltr", "placeholder": "https://"}),
            "instagram": forms.TextInput(attrs={"dir": "ltr", "placeholder": "username"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._old_avatar_name = self.instance.avatar.name if self.instance.pk and self.instance.avatar else ""
        self.fields["avatar"].help_text = "JPG، PNG یا WebP — حداکثر ۲ مگابایت"

    def clean_instagram(self):
        value = self.cleaned_data.get("instagram", "").strip().lstrip("@")
        if value and not re.fullmatch(r"[A-Za-z0-9._]{1,30}", value):
            raise ValidationError("نام کاربری اینستاگرام فقط شامل حروف انگلیسی، عدد، نقطه و _ است.")
        return value

    def save(self, commit=True):
        profile = super().save(commit=commit)
        if commit and "avatar" in self.changed_data and self._old_avatar_name:
            if self._old_avatar_name != (profile.avatar.name if profile.avatar else ""):
                profile.avatar.storage.delete(self._old_avatar_name)  # حذف فایل قدیمی
        return profile


# ─────────────────────────── رمز عبور ───────────────────────────
class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "رمز عبور فعلی"
        self.fields["new_password1"].label = "رمز عبور جدید"
        self.fields["new_password2"].label = "تکرار رمز عبور جدید"
        for name in self.fields:
            self.fields[name].widget.attrs["dir"] = "ltr"


class StyledPasswordResetForm(StyledFormMixin, PasswordResetForm):
    email = forms.EmailField(
        label="ایمیل حساب",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "dir": "ltr", "autofocus": True}),
    )


class StyledSetPasswordForm(StyledFormMixin, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = "رمز عبور جدید"
        self.fields["new_password2"].label = "تکرار رمز عبور جدید"
        for name in self.fields:
            self.fields[name].widget.attrs["dir"] = "ltr"


# ─────────────────────────── پنل مدیریت کاربران ───────────────────────────
class ManageUserForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "role", "is_active", "email_verified")

    def __init__(self, *args, acting_user=None, **kwargs):
        self.acting_user = acting_user
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["dir"] = "ltr"

    def clean(self):
        cleaned = super().clean()
        # جلوگیری از قفل‌شدن مدیر از سیستم
        if self.acting_user and self.instance.pk == self.acting_user.pk:
            if cleaned.get("is_active") is False:
                self.add_error("is_active", "نمی‌توانید حساب خودتان را غیرفعال کنید.")
            if "role" in cleaned and cleaned["role"] != self.instance.role and not self.acting_user.is_superuser:
                self.add_error("role", "نمی‌توانید نقش خودتان را تغییر دهید.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if "email_verified" in self.changed_data:
            user.email_verified_at = timezone.now() if user.email_verified else None
        if commit:
            user.save()
        return user
