import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token

logger = logging.getLogger(__name__)


def build_verification_url(request, user) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    path = reverse("accounts:verify_email", kwargs={"uidb64": uid, "token": token})
    return request.build_absolute_uri(path)


def send_verification_email(request, user) -> bool:
    """ایمیل تأیید را می‌فرستد. در صورت خطا False برمی‌گرداند (و لاگ می‌کند)."""
    if not user.email:
        return False
    context = {
        "user": user,
        "verify_url": build_verification_url(request, user),
        "brand": settings.SITE_NAME,
        "valid_hours": settings.PASSWORD_RESET_TIMEOUT // 3600,
    }
    message = EmailMultiAlternatives(
        subject=f"تأیید ایمیل حساب {settings.SITE_NAME}",
        body=render_to_string("accounts/emails/verify_email.txt", context),
        to=[user.email],
    )
    message.attach_alternative(render_to_string("accounts/emails/verify_email.html", context), "text/html")
    try:
        message.send()
    except Exception:  # noqa: BLE001 — خطای SMTP نباید ثبت‌نام را خراب کند
        logger.exception("ارسال ایمیل تأیید برای کاربر %s ناموفق بود", user.pk)
        return False
    return True


def dev_email_hint(request) -> None:
    """
    در حالت توسعه (EMAIL_BACKEND=console) ایمیل واقعی ارسال نمی‌شود و متن ایمیل در ترمینال چاپ می‌شود.
    این پیام به کاربر/توسعه‌دهنده می‌گوید لینک را کجا پیدا کند.
    """
    if settings.DEBUG and settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
        messages.info(
            request,
            "حالت توسعه: ایمیل واقعی فرستاده نمی‌شود؛ لینک تأیید را در ترمینال (پنجرهٔ runserver) ببینید.",
        )
