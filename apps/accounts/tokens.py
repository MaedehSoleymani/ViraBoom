from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    توکن یک‌بارمصرف تأیید ایمیل.
    چون email و email_verified در hash هستند، با تغییر ایمیل یا بعد از تأیید، لینک قبلی باطل می‌شود.
    """

    key_salt = "apps.accounts.tokens.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.email_verified}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()
