from django import template

from ..jalali import format_jalali

register = template.Library()


@register.filter(name="jdate")
def jdate(value, fmt="Y/m/d"):
    """{{ value|jdate }} یا {{ value|jdate:"j F Y" }} — تاریخ شمسی با ارقام فارسی."""
    return format_jalali(value, fmt)
