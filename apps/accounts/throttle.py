"""
محدودکنندهٔ ساده بر پایهٔ کش Django:
  • قفل موقت پس از چند ورود ناموفق (ضد brute-force)
  • فاصلهٔ زمانی بین ارسال‌های پشت‌سرهم ایمیل
"""
from django.core.cache import cache

MAX_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60


def _login_key(phone: str, ip: str) -> str:
    return f"accounts:login-fail:{phone}:{ip}"


def is_locked(phone: str, ip: str) -> bool:
    return cache.get(_login_key(phone, ip), 0) >= MAX_ATTEMPTS


def register_failure(phone: str, ip: str) -> None:
    key = _login_key(phone, ip)
    try:
        cache.incr(key)
    except ValueError:  # کلید هنوز وجود ندارد
        cache.set(key, 1, LOCK_SECONDS)


def reset_failures(phone: str, ip: str) -> None:
    cache.delete(_login_key(phone, ip))


def allow_action(name: str, ident, seconds: int) -> bool:
    """True یعنی مجاز است و تا `seconds` ثانیهٔ بعد دوباره مجاز نخواهد بود."""
    return cache.add(f"accounts:cooldown:{name}:{ident}", 1, seconds)
