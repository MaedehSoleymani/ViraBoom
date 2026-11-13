"""ابزارهای کوچک مشترک: نرمال‌سازی شماره موبایل، ماسک‌کردن، IP کلاینت."""
import re

# ارقام فارسی و عربی → لاتین
_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_phone(value) -> str:
    """
    هر قالبی از شماره موبایل ایران را به شکل استاندارد 09xxxxxxxxx تبدیل می‌کند.
    نمونه‌ها: «۰۹۱۲ ۱۲۳ ۴۵۶۷»، «+98 912 123 4567»، «9121234567»، «00989121234567».
    اگر الگو ناشناخته باشد، رشتهٔ تمیزشده برگردانده می‌شود تا اعتبارسنج خطا بدهد.
    """
    if value is None:
        return ""
    value = str(value).translate(_DIGIT_MAP)
    value = re.sub(r"[\s\-()._]", "", value)
    if value.startswith("+98"):
        value = "0" + value[3:]
    elif value.startswith("0098"):
        value = "0" + value[4:]
    elif value.startswith("98") and len(value) == 12:
        value = "0" + value[2:]
    elif value.startswith("9") and len(value) == 10:
        value = "0" + value
    return value


def mask_phone(phone: str) -> str:
    """09121234567 → 0912***4567"""
    if not phone or len(phone) < 8:
        return phone or ""
    return f"{phone[:4]}***{phone[-4:]}"


def get_client_ip(request) -> str:
    """
    IP کلاینت. عمداً فقط REMOTE_ADDR را می‌خوانیم تا هدر جعلی X-Forwarded-For
    دور محدودیت تلاش ورود را نزند. پشت reverse proxy آن را طبق زیرساخت تنظیم کنید.
    """
    if request is None:
        return ""
    return request.META.get("REMOTE_ADDR", "")
