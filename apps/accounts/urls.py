from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # احراز هویت
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),  # فقط POST
    # تأیید ایمیل
    path("verify-email/sent/", views.VerifyEmailSentView.as_view(), name="verify_email_sent"),
    path("verify-email/resend/", views.ResendVerificationView.as_view(), name="verify_email_resend"),
    path("verify-email/<uidb64>/<token>/", views.VerifyEmailView.as_view(), name="verify_email"),
    # رمز عبور
    path("password/forgot/", views.PasswordResetView.as_view(), name="password_reset"),
    path("password/forgot/sent/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password/reset/done/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("password/change/", views.PasswordChangeView.as_view(), name="password_change"),
    # حساب کاربری
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    # پنل مدیریت کاربران
    path("panel/users/", views.UserListView.as_view(), name="user_list"),
    path("panel/users/<int:pk>/", views.UserManageView.as_view(), name="user_manage"),
    path("panel/users/<int:pk>/toggle-active/", views.UserToggleActiveView.as_view(), name="user_toggle_active"),
]
