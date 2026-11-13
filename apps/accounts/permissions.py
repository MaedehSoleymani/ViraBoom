"""
دسترسی بر اساس نقش — این ابزارها را هم‌تیمی‌ها هم می‌توانند استفاده کنند:

    from apps.accounts.permissions import role_required, email_verified_required, RoleRequiredMixin
    from apps.accounts.models import Role

    @role_required(Role.CREATOR, Role.ADMIN)
    def upload_design(request): ...

    @email_verified_required      # مثلاً قبل از پرداخت
    def checkout(request): ...
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import Role


def role_required(*roles):
    """کاربر باید لاگین باشد و یکی از نقش‌ها را داشته باشد (superuser همیشه مجاز است)."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.has_role(*roles):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return login_required(_wrapped)

    return decorator


def email_verified_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.email_verified:
            messages.warning(request, "برای ادامه، ابتدا ایمیل خود را تأیید کنید.")
            return redirect("accounts:verify_email_sent")
        return view_func(request, *args, **kwargs)

    return login_required(_wrapped)


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """برای کلاس‌ویوها: allowed_roles = (Role.ADMIN, ...). ناشناس → ورود، بدون دسترسی → ۴۰۳."""

    allowed_roles: tuple = ()

    def test_func(self):
        return self.request.user.has_role(*self.allowed_roles)


class ManagerRequiredMixin(RoleRequiredMixin):
    allowed_roles = (Role.ADMIN,)
