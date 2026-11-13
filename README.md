# Viraboom — بخش Accounts (نفر اول)

## راه‌اندازی (قدم‌به‌قدم)

```bash
# ۱) محیط مجازی و نصب وابستگی‌ها
python -m venv venv
source venv/bin/activate        # ویندوز: venv\Scripts\activate
pip install -r requirements.txt

# ۲) ساخت migration (حتماً قبل از اولین migrate؛ چون User سفارشی داریم)
python manage.py makemigrations accounts
python manage.py migrate

# ۳) ساخت مدیر کل
python manage.py createsuperuser     # موبایل، ایمیل، رمز

# ۴) اجرای تست‌ها
python manage.py test apps.accounts -v 2

# ۵) اجرای سایت
python manage.py runserver
```

نکته: اگر قبلاً با User پیش‌فرض جنگو `migrate` زده‌اید، `db.sqlite3` را پاک کنید و دوباره از قدم ۲ شروع کنید.

## آدرس‌ها

| آدرس | کار |
|---|---|
| /accounts/register/ | ثبت‌نام |
| /accounts/login/ | ورود با موبایل + رمز |
| /accounts/logout/ | خروج (فقط POST) |
| /accounts/verify-email/sent/ | راهنمای تأیید ایمیل + ارسال مجدد |
| /accounts/password/forgot/ | فراموشی رمز (ارسال لینک به ایمیل) |
| /accounts/password/change/ | تغییر رمز |
| /accounts/dashboard/ | داشبورد کاربر |
| /accounts/profile/ | ویرایش پروفایل |
| /accounts/panel/users/ | پنل مدیریت کاربران (فقط مدیر) |

## برای هم‌تیمی‌ها

```python
from apps.accounts.permissions import role_required, email_verified_required, RoleRequiredMixin
from apps.accounts.models import Role

@role_required(Role.CREATOR, Role.ADMIN)   # فقط طراح یا مدیر
@email_verified_required                   # فقط ایمیل تأییدشده (مثلاً قبل از پرداخت)

# در مدل‌های خودتان:
user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
```
- هرگز `from django.contrib.auth.models import User` ننویسید؛ از `settings.AUTH_USER_MODEL` یا `get_user_model()` استفاده کنید.
- صفحهٔ اصلی موقت `templates/home.html` است؛ نفر دوم جایگزینش می‌کند و فقط `name="home"` را نگه می‌دارد.
- لینک سفارش‌ها و دانلودها را در `account_base.html` (سایدبار) و `dashboard.html` اضافه کنید.

## فونت
فونت Vazirmatn از Google Fonts لود می‌شود. برای پایداری در ایران بهتر است فایل‌های فونت را داخل `static/fonts/` بگذارید و با `@font-face` در `main.css` لود کنید.

## ایمیل
- پیش‌فرض (توسعه): ایمیل‌ها **داخل ترمینال runserver چاپ می‌شوند** و به صندوق واقعی نمی‌رسند. لینک تأیید را از همان‌جا کپی کنید.
- ارسال واقعی: `.env.example` را به `.env` کپی کنید و بخش ایمیل را باز (uncomment) و پر کنید. تست ارسال: `python manage.py sendtestemail you@example.com`
- تاریخ‌ها در قالب‌ها شمسی‌اند: `{% load jalali_tags %}` و `{{ value|jdate:"j F Y" }}`
