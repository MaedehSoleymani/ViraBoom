import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.views import View
from django.views.generic import FormView, ListView, TemplateView, UpdateView

from . import throttle
from .emails import dev_email_hint, send_verification_email
from .forms import (
    LoginForm,
    ManageUserForm,
    ProfileDetailsForm,
    ProfileUserForm,
    RegisterForm,
    StyledPasswordChangeForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)
from .models import Profile, Role, User
from .permissions import ManagerRequiredMixin
from .tokens import email_verification_token
from .utils import normalize_phone

logger = logging.getLogger(__name__)
MODEL_BACKEND = "django.contrib.auth.backends.ModelBackend"
VERIFY_COOLDOWN_SECONDS = 60


class AnonymousOnlyMixin:
    """کاربر لاگین‌کرده به صفحات ورود/ثبت‌نام/فراموشی نیازی ندارد."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)


# ─────────────────────────── ثبت‌نام / ورود ───────────────────────────
class RegisterView(AnonymousOnlyMixin, FormView):
    template_name = "accounts/register.html"
    form_class = RegisterForm

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend=MODEL_BACKEND)
        throttle.allow_action("verify-mail", user.pk, VERIFY_COOLDOWN_SECONDS)
        if send_verification_email(self.request, user):
            messages.success(self.request, "حساب شما ساخته شد. لینک تأیید به ایمیلتان ارسال شد.")
            dev_email_hint(self.request)
        else:
            messages.warning(self.request, "حساب ساخته شد، اما ارسال ایمیل تأیید ناموفق بود. بعداً دوباره درخواست دهید.")
        return redirect("accounts:verify_email_sent")


class LoginView(AnonymousOnlyMixin, FormView):
    template_name = "accounts/login.html"
    form_class = LoginForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["next"] = self.request.POST.get("next") or self.request.GET.get("next", "")
        return ctx

    def form_valid(self, form):
        login(self.request, form.user)
        if not form.cleaned_data["remember_me"]:
            self.request.session.set_expiry(0)  # با بستن مرورگر تمام می‌شود
        messages.success(self.request, f"خوش آمدید {form.user.get_short_name()}!")
        return redirect(self.get_success_url())

    def get_success_url(self):
        target = self.request.POST.get("next") or self.request.GET.get("next")
        if target and url_has_allowed_host_and_scheme(
            target, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure()
        ):
            return target
        return resolve_url(settings.LOGIN_REDIRECT_URL)


# خروج: از LogoutView خود جنگو (فقط POST) در urls.py استفاده می‌شود.


# ─────────────────────────── تأیید ایمیل ───────────────────────────
class VerifyEmailSentView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/verify_email_sent.html"


class ResendVerificationView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        user = request.user
        if user.email_verified:
            messages.info(request, "ایمیل شما قبلاً تأیید شده است.")
            return redirect("accounts:dashboard")
        if not throttle.allow_action("verify-mail", user.pk, VERIFY_COOLDOWN_SECONDS):
            messages.warning(request, "ایمیل تأیید به‌تازگی ارسال شده؛ لطفاً یک دقیقه صبر کنید.")
        elif send_verification_email(request, user):
            messages.success(request, "ایمیل تأیید دوباره ارسال شد.")
            dev_email_hint(request)
        else:
            messages.error(request, "ارسال ایمیل ناموفق بود. کمی بعد دوباره تلاش کنید.")
        return redirect("accounts:verify_email_sent")


class VerifyEmailView(View):
    def get(self, request, uidb64, token):
        user = None
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            pass

        if user is not None and user.email_verified:
            messages.info(request, "ایمیل شما قبلاً تأیید شده است.")
        elif user is not None and email_verification_token.check_token(user, token):
            user.mark_email_verified()
            messages.success(request, "ایمیل شما با موفقیت تأیید شد.")
        else:
            messages.error(request, "لینک تأیید نامعتبر یا منقضی شده است. از داشبورد، لینک جدید بگیرید.")

        return redirect("accounts:dashboard" if request.user.is_authenticated else "accounts:login")


# ─────────────────────────── رمز عبور ───────────────────────────
class PasswordResetView(AnonymousOnlyMixin, auth_views.PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    form_class = StyledPasswordResetForm
    email_template_name = "accounts/emails/password_reset.txt"
    html_email_template_name = "accounts/emails/password_reset.html"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    extra_email_context = {"brand": settings.SITE_NAME}


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    form_class = StyledSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy("accounts:dashboard")

    def form_valid(self, form):
        messages.success(self.request, "رمز عبور شما تغییر کرد.")
        return super().form_valid(form)


# ─────────────────────────── داشبورد و پروفایل ───────────────────────────
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        ctx["profile"] = profile
        ctx["completion"] = profile.completion_percent
        # ← هم‌تیمی‌ها می‌توانند اینجا (یا در قالب) آمار سفارش‌ها و دانلودها را اضافه کنند.
        return ctx


class ProfileView(LoginRequiredMixin, View):
    template_name = "accounts/profile.html"

    def _build_forms(self, request, data=None, files=None):
        user = User.objects.get(pk=request.user.pk)  # نمونهٔ تازه تا فرم نامعتبر روی request.user اثر نگذارد
        profile, _ = Profile.objects.get_or_create(user=user)
        return (
            ProfileUserForm(data, instance=user),
            ProfileDetailsForm(data, files, instance=profile),
        )

    def _render(self, request, user_form, details_form):
        return render(request, self.template_name, {"user_form": user_form, "details_form": details_form})

    def get(self, request):
        return self._render(request, *self._build_forms(request))

    def post(self, request):
        user_form, details_form = self._build_forms(request, request.POST, request.FILES)
        if not (user_form.is_valid() and details_form.is_valid()):
            messages.error(request, "لطفاً خطاهای فرم را برطرف کنید.")
            return self._render(request, user_form, details_form)

        email_changed = "email" in user_form.changed_data
        with transaction.atomic():
            user = user_form.save()
            details_form.save()
            if email_changed:
                user.email_verified = False
                user.email_verified_at = None
                user.save(update_fields=["email_verified", "email_verified_at"])

        if email_changed:
            throttle.allow_action("verify-mail", user.pk, VERIFY_COOLDOWN_SECONDS)
            send_verification_email(request, user)
            messages.info(request, "ایمیل جدید ثبت شد. لینک تأیید برایتان ارسال شد.")
            dev_email_hint(request)
        messages.success(request, "پروفایل شما ذخیره شد.")
        return redirect("accounts:profile")


# ─────────────────────────── پنل مدیریت کاربران ───────────────────────────
class UserListView(ManagerRequiredMixin, ListView):
    model = User
    template_name = "accounts/panel/user_list.html"
    context_object_name = "users"
    paginate_by = 15

    def get_queryset(self):
        qs = User.objects.order_by("-date_joined")
        g = self.request.GET
        q = g.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(phone__icontains=normalize_phone(q))
                | Q(email__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )
        if g.get("role") in Role.values:
            qs = qs.filter(role=g["role"])
        if g.get("status") in {"active", "inactive"}:
            qs = qs.filter(is_active=g["status"] == "active")
        if g.get("verified") in {"yes", "no"}:
            qs = qs.filter(email_verified=g["verified"] == "yes")
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        ctx["roles"] = Role.choices
        ctx["filters"] = {k: self.request.GET.get(k, "") for k in ("q", "role", "status", "verified")}
        ctx["stats"] = User.objects.aggregate(
            total=Count("pk"),
            active=Count("pk", filter=Q(is_active=True)),
            unverified=Count("pk", filter=Q(email_verified=False)),
            managers=Count("pk", filter=Q(role__in=[Role.ADMIN, Role.SUPPORT])),
        )
        return ctx


class UserManageView(ManagerRequiredMixin, UpdateView):
    model = User
    form_class = ManageUserForm
    template_name = "accounts/panel/user_detail.html"
    context_object_name = "managed_user"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.is_superuser and not self.request.user.is_superuser:
            raise PermissionDenied
        return obj

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["acting_user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "تغییرات کاربر ذخیره شد.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.path


class UserToggleActiveView(ManagerRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if target.pk == request.user.pk:
            messages.error(request, "نمی‌توانید حساب خودتان را غیرفعال کنید.")
        elif target.is_superuser and not request.user.is_superuser:
            raise PermissionDenied
        else:
            target.is_active = not target.is_active
            target.save(update_fields=["is_active"])
            state = "فعال" if target.is_active else "غیرفعال"
            messages.success(request, f"حساب {target.display_name} {state} شد.")
        nxt = request.POST.get("next")
        if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
            return redirect(nxt)
        return redirect("accounts:user_list")
