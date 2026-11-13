import re
from datetime import datetime, timezone as dt_timezone
from urllib.parse import urlparse

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from .jalali import format_jalali, gregorian_to_jalali
from .models import Profile, Role, User
from .utils import normalize_phone

PASSWORD = "Str0ng!Pass#2026"
FAST_HASHER = ["django.contrib.auth.hashers.MD5PasswordHasher"]


def make_user(phone="09121234567", email="ali@example.com", password=PASSWORD, **extra):
    return User.objects.create_user(phone=phone, password=password, email=email, **extra)


@override_settings(PASSWORD_HASHERS=FAST_HASHER)
class BaseTestCase(TestCase):
    def setUp(self):
        cache.clear()


# ───────────────────────── ابزارها و مدل ─────────────────────────
class PhoneNormalizationTests(TestCase):
    def test_variants(self):
        for raw in ["09121234567", "۰۹۱۲۱۲۳۴۵۶۷", "+989121234567", "00989121234567", "9121234567", "0912 123 4567", "0912-123-4567"]:
            self.assertEqual(normalize_phone(raw), "09121234567", raw)

    def test_garbage_is_left_invalid(self):
        self.assertNotRegex(normalize_phone("abc"), r"^09\d{9}$")


class UserModelTests(BaseTestCase):
    def test_create_user_normalizes_and_creates_profile(self):
        user = make_user(phone="+989121234567", email="ALI@Example.com")
        self.assertEqual(user.phone, "09121234567")
        self.assertEqual(user.email, "ali@example.com")
        self.assertEqual(user.role, Role.CUSTOMER)
        self.assertFalse(user.is_staff)
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_superuser(self):
        admin = User.objects.create_superuser("09120000000", "x", email="a@b.com")
        self.assertTrue(admin.is_superuser and admin.is_staff)
        self.assertEqual(admin.role, Role.ADMIN)

    def test_staff_flag_follows_role(self):
        user = make_user(role=Role.SUPPORT)
        self.assertTrue(user.is_staff)
        user.role = Role.CREATOR
        user.save()
        self.assertFalse(user.is_staff)

    def test_empty_email_is_none(self):
        a = User.objects.create_user("09121111111", PASSWORD, email="")
        b = User.objects.create_user("09122222222", PASSWORD, email="")
        self.assertIsNone(a.email)
        self.assertIsNone(b.email)  # unique نباید خطا بدهد


# ───────────────────────── ثبت‌نام و تأیید ایمیل ─────────────────────────
class RegisterTests(BaseTestCase):
    url = reverse("accounts:register")
    data = {
        "first_name": "علی",
        "last_name": "رضایی",
        "phone": "۰۹۱۲۱۲۳۴۵۶۷",
        "email": "Ali@Example.com",
        "password1": PASSWORD,
        "password2": PASSWORD,
        "accept_terms": "on",
    }

    def test_page_renders_and_is_noindex(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'content="noindex, follow"')

    def test_register_success(self):
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, reverse("accounts:verify_email_sent"))
        user = User.objects.get(phone="09121234567")
        self.assertEqual(user.email, "ali@example.com")
        self.assertEqual(user.role, Role.CUSTOMER)
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("_auth_user_id", self.client.session)

    def test_cannot_choose_role(self):
        self.client.post(self.url, {**self.data, "role": "admin", "is_superuser": "on"})
        user = User.objects.get(phone="09121234567")
        self.assertEqual(user.role, Role.CUSTOMER)
        self.assertFalse(user.is_superuser)

    def test_duplicate_phone_and_email(self):
        make_user()
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertTrue(response.context["form"].errors.get("phone"))
        self.assertTrue(response.context["form"].errors.get("email"))

    def test_password_mismatch_and_weak(self):
        response = self.client.post(self.url, {**self.data, "password2": "different"})
        self.assertTrue(response.context["form"].errors.get("password2"))
        response = self.client.post(self.url, {**self.data, "password1": "12345678", "password2": "12345678"})
        self.assertTrue(response.context["form"].errors.get("password1"))
        self.assertEqual(User.objects.count(), 0)

    def test_invalid_phone(self):
        response = self.client.post(self.url, {**self.data, "phone": "12345"})
        self.assertTrue(response.context["form"].errors.get("phone"))

    def test_terms_required(self):
        data = {k: v for k, v in self.data.items() if k != "accept_terms"}
        response = self.client.post(self.url, data)
        self.assertTrue(response.context["form"].errors.get("accept_terms"))

    def test_authenticated_user_is_redirected(self):
        self.client.force_login(make_user())
        self.assertRedirects(self.client.get(self.url), reverse("accounts:dashboard"))


class EmailVerificationTests(BaseTestCase):
    def _register_and_get_link(self):
        self.client.post(RegisterTests.url, RegisterTests.data)
        match = re.search(r"http://testserver\S+", mail.outbox[0].body)
        self.assertIsNotNone(match)
        return urlparse(match.group(0)).path

    def test_verification_flow(self):
        path = self._register_and_get_link()
        response = self.client.get(path)
        self.assertRedirects(response, reverse("accounts:dashboard"))
        user = User.objects.get(phone="09121234567")
        self.assertTrue(user.email_verified)
        self.assertIsNotNone(user.email_verified_at)

    def test_link_works_when_logged_out_and_is_idempotent(self):
        path = self._register_and_get_link()
        self.client.logout()
        self.assertRedirects(self.client.get(path), reverse("accounts:login"))
        self.assertTrue(User.objects.get(phone="09121234567").email_verified)
        self.client.get(path)  # بار دوم نباید خطا بدهد

    def test_tampered_token_rejected(self):
        path = self._register_and_get_link()
        self.client.get(path.rsplit("/", 2)[0] + "/bad-token/")
        self.assertFalse(User.objects.get(phone="09121234567").email_verified)

    def test_resend_has_cooldown(self):
        self.client.force_login(make_user())
        self.client.post(reverse("accounts:verify_email_resend"))
        self.client.post(reverse("accounts:verify_email_resend"))
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_requires_post(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse("accounts:verify_email_resend")).status_code, 405)


# ───────────────────────── ورود و خروج ─────────────────────────
class LoginTests(BaseTestCase):
    url = reverse("accounts:login")

    def setUp(self):
        super().setUp()
        self.user = make_user()

    def test_login_success_with_various_phone_formats(self):
        for phone in ["09121234567", "+989121234567", "۰۹۱۲۱۲۳۴۵۶۷"]:
            self.client.logout()
            response = self.client.post(self.url, {"phone": phone, "password": PASSWORD})
            self.assertRedirects(response, reverse("accounts:dashboard"), msg_prefix=phone)

    def test_wrong_password_gives_generic_error(self):
        response = self.client.post(self.url, {"phone": "09121234567", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "شماره موبایل یا رمز عبور اشتباه است")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unknown_phone_same_error(self):
        response = self.client.post(self.url, {"phone": "09129999999", "password": PASSWORD})
        self.assertContains(response, "شماره موبایل یا رمز عبور اشتباه است")

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        self.client.post(self.url, {"phone": "09121234567", "password": PASSWORD})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_lockout_after_repeated_failures(self):
        for _ in range(5):
            self.client.post(self.url, {"phone": "09121234567", "password": "wrong"})
        response = self.client.post(self.url, {"phone": "09121234567", "password": PASSWORD})
        self.assertContains(response, "تلاش‌های ناموفق")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_remember_me(self):
        self.client.post(self.url, {"phone": "09121234567", "password": PASSWORD})
        self.assertTrue(self.client.session.get_expire_at_browser_close())
        self.client.logout()
        self.client.post(self.url, {"phone": "09121234567", "password": PASSWORD, "remember_me": "on"})
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_next_redirect_safe_and_unsafe(self):
        data = {"phone": "09121234567", "password": PASSWORD}
        response = self.client.post(self.url, {**data, "next": reverse("accounts:profile")})
        self.assertRedirects(response, reverse("accounts:profile"))
        self.client.logout()
        response = self.client.post(self.url, {**data, "next": "https://evil.example.com/"})
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)


# ───────────────────────── رمز عبور ─────────────────────────
class PasswordTests(BaseTestCase):
    def test_reset_flow(self):
        user = make_user()
        response = self.client.post(reverse("accounts:password_reset"), {"email": "ali@example.com"})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        link = re.search(r"http://testserver(\S+)", mail.outbox[0].body).group(1)

        response = self.client.get(link, follow=True)
        confirm_url = response.redirect_chain[-1][0]
        new_password = "An0ther!Secret#77"
        response = self.client.post(confirm_url, {"new_password1": new_password, "new_password2": new_password})
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))

        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))
        self.client.logout()
        response = self.client.post(reverse("accounts:login"), {"phone": "09121234567", "password": new_password})
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_reset_unknown_email_does_not_leak(self):
        response = self.client.post(reverse("accounts:password_reset"), {"email": "nobody@example.com"})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_change_password(self):
        user = make_user()
        self.client.force_login(user)
        new_password = "Newer!Secret#2026"
        response = self.client.post(
            reverse("accounts:password_change"),
            {"old_password": PASSWORD, "new_password1": new_password, "new_password2": new_password},
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))
        # نشست فعلی باید معتبر بماند
        self.assertEqual(self.client.get(reverse("accounts:dashboard")).status_code, 200)

    def test_change_password_wrong_old(self):
        self.client.force_login(make_user())
        response = self.client.post(
            reverse("accounts:password_change"),
            {"old_password": "bad", "new_password1": "Newer!Secret#2026", "new_password2": "Newer!Secret#2026"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors.get("old_password"))


# ───────────────────────── داشبورد و پروفایل ─────────────────────────
class DashboardProfileTests(BaseTestCase):
    def test_login_required(self):
        for name in ("dashboard", "profile", "password_change", "verify_email_sent"):
            url = reverse(f"accounts:{name}")
            self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}")

    def test_dashboard_renders(self):
        user = make_user(first_name="علی", last_name="رضایی")
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "علی رضایی")

    def test_profile_update(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:profile"),
            {"first_name": "علی", "last_name": "رضایی", "email": "ali@example.com", "bio": "طراح", "city": "تهران", "instagram": "@ali.design"},
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        self.assertEqual((user.first_name, user.profile.city, user.profile.instagram), ("علی", "تهران", "ali.design"))

    def test_changing_email_resets_verification(self):
        user = make_user()
        user.mark_email_verified()
        self.client.force_login(user)
        self.client.post(
            reverse("accounts:profile"),
            {"first_name": "علی", "last_name": "رضایی", "email": "new@example.com"},
        )
        user.refresh_from_db()
        self.assertEqual(user.email, "new@example.com")
        self.assertFalse(user.email_verified)
        self.assertEqual(mail.outbox[-1].to, ["new@example.com"])

    def test_phone_cannot_be_changed_via_profile(self):
        user = make_user()
        self.client.force_login(user)
        self.client.post(
            reverse("accounts:profile"),
            {"first_name": "علی", "last_name": "رضایی", "email": "ali@example.com", "phone": "09350000000"},
        )
        user.refresh_from_db()
        self.assertEqual(user.phone, "09121234567")


# ───────────────────────── نقش‌ها و پنل مدیریت ─────────────────────────
class PanelPermissionTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin = make_user("09120000001", "admin@example.com", role=Role.ADMIN)
        self.customer = make_user("09120000002", "c@example.com")
        self.support = make_user("09120000003", "s@example.com", role=Role.SUPPORT)

    def test_anonymous_redirected_to_login(self):
        url = reverse("accounts:user_list")
        self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}")

    def test_customer_and_support_forbidden(self):
        for user in (self.customer, self.support):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 403)
            self.assertEqual(self.client.get(reverse("accounts:user_manage", args=[self.admin.pk])).status_code, 403)

    def test_admin_can_list_search_and_filter(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:user_list"), {"q": "۰۹۱۲۰۰۰۰۰۰۲"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([u.pk for u in response.context["users"]], [self.customer.pk])
        response = self.client.get(reverse("accounts:user_list"), {"role": Role.SUPPORT})
        self.assertEqual([u.pk for u in response.context["users"]], [self.support.pk])

    def test_admin_changes_role(self):
        self.client.force_login(self.admin)
        url = reverse("accounts:user_manage", args=[self.customer.pk])
        response = self.client.post(
            url,
            {"first_name": "x", "last_name": "y", "email": "c@example.com", "role": Role.CREATOR, "is_active": "on"},
        )
        self.assertRedirects(response, url)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, Role.CREATOR)

    def test_toggle_active(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:user_toggle_active", args=[self.customer.pk]))
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)

    def test_admin_cannot_deactivate_self(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:user_toggle_active", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_cannot_touch_superuser(self):
        root = User.objects.create_superuser("09123333333", "x", email="root@example.com")
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("accounts:user_manage", args=[root.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("accounts:user_toggle_active", args=[root.pk])).status_code, 403)
        root.refresh_from_db()
        self.assertTrue(root.is_active)

    def test_toggle_requires_post(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("accounts:user_toggle_active", args=[self.customer.pk])).status_code, 405)


# ───────────────────────── تاریخ شمسی ─────────────────────────
class JalaliTests(BaseTestCase):
    def test_known_conversions(self):
        cases = {
            (2026, 3, 21): (1405, 1, 1),
            (2025, 3, 21): (1404, 1, 1),
            (2025, 3, 20): (1403, 12, 30),  # ۱۴۰۳ کبیسه بود
            (2024, 3, 20): (1403, 1, 1),
            (2026, 11, 13): (1405, 8, 22),
            (2026, 9, 23): (1405, 7, 1),
        }
        for greg, expected in cases.items():
            self.assertEqual(gregorian_to_jalali(*greg), expected, greg)

    def test_format_uses_persian_digits_and_month_names(self):
        value = datetime(2026, 11, 13, 10, 5, tzinfo=dt_timezone.utc)
        self.assertEqual(format_jalali(value, "j F Y"), "۲۲ آبان ۱۴۰۵")
        self.assertEqual(format_jalali(value, "Y/m/d"), "۱۴۰۵/۰۸/۲۲")

    def test_aware_datetime_is_converted_to_tehran_time(self):
        # ۲۲:۰۰ UTC = ۰۱:۳۰ بامداد روز بعد به وقت تهران → ۲۳ آبان
        value = datetime(2026, 11, 13, 22, 0, tzinfo=dt_timezone.utc)
        self.assertEqual(format_jalali(value, "Y/m/d H:i"), "۱۴۰۵/۰۸/۲۳ ۰۱:۳۰")

    def test_empty_values(self):
        self.assertEqual(format_jalali(None), "")
        self.assertEqual(format_jalali("not-a-date"), "")

    def test_dashboard_shows_jalali_join_date(self):
        user = make_user()
        user.date_joined = datetime(2026, 11, 13, 10, 0, tzinfo=dt_timezone.utc)
        user.save()
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertContains(response, "۲۲ آبان ۱۴۰۵")
