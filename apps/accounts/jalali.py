"""
تبدیل تاریخ میلادی به شمسی (جلالی) — بدون وابستگی خارجی.

استفاده در قالب‌ها از طریق فیلتر `jdate` (فایل templatetags/jalali_tags.py):
    {% load jalali_tags %}
    {{ user.date_joined|jdate:"j F Y" }}      →  ۲۲ آبان ۱۴۰۵
    {{ user.date_joined|jdate:"Y/m/d H:i" }}  →  ۱۴۰۵/۰۸/۲۲ ۱۳:۴۵
"""
from datetime import date, datetime

from django.utils import timezone

JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]
_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """الگوریتم حسابی استاندارد (دورهٔ ۳۳ ساله)؛ خروجی: (سال، ماه، روز) شمسی."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400)
        + gd + g_d_m[gm - 1]
    )
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def format_jalali(value, fmt: str = "Y/m/d", persian_digits: bool = True) -> str:
    """
    value: datetime یا date. datetime آگاه از منطقهٔ زمانی ابتدا به زمان محلی (Asia/Tehran) تبدیل می‌شود.
    توکن‌ها: Y سال ۴رقمی · y سال ۲رقمی · m ماه ۲رقمی · n ماه · d روز ۲رقمی · j روز · F نام ماه · H ساعت · i دقیقه
    """
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
    elif not isinstance(value, date):
        return ""

    jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
    hour = getattr(value, "hour", 0)
    minute = getattr(value, "minute", 0)
    tokens = {
        "Y": f"{jy:04d}",
        "y": f"{jy % 100:02d}",
        "m": f"{jm:02d}",
        "n": str(jm),
        "d": f"{jd:02d}",
        "j": str(jd),
        "F": JALALI_MONTHS[jm - 1],
        "H": f"{hour:02d}",
        "i": f"{minute:02d}",
    }
    result = "".join(tokens.get(ch, ch) for ch in fmt)
    return result.translate(_PERSIAN_DIGITS) if persian_digits else result
