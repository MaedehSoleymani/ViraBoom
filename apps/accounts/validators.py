import re

from django.core.exceptions import ValidationError

PHONE_RE = re.compile(r"^09\d{9}$")
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # ۲ مگابایت


def validate_iranian_mobile(value: str) -> None:
    if not PHONE_RE.match(value or ""):
        raise ValidationError(
            "شماره موبایل معتبر نیست. نمونهٔ درست: 09121234567",
            code="invalid_phone",
        )


def validate_image_size(file) -> None:
    if file and file.size > MAX_AVATAR_BYTES:
        raise ValidationError("حجم تصویر نباید بیشتر از ۲ مگابایت باشد.", code="file_too_large")
