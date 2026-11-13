from django import forms
from django.contrib import admin
from django.contrib.auth import password_validation
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm

from .forms import PhoneField
from .models import Profile, User


class AdminUserCreationForm(forms.ModelForm):
    phone = PhoneField()
    password1 = forms.CharField(label="رمز عبور", strip=False, widget=forms.PasswordInput)
    password2 = forms.CharField(label="تکرار رمز عبور", strip=False, widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("phone", "email", "first_name", "last_name", "role")

    def clean_password2(self):
        p1, p2 = self.cleaned_data.get("password1"), self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("رمزهای عبور یکسان نیستند.")
        return p2

    def _post_clean(self):
        super()._post_clean()
        if self.cleaned_data.get("password2"):
            try:
                password_validation.validate_password(self.cleaned_data["password2"], self.instance)
            except forms.ValidationError as exc:
                self.add_error("password2", exc)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class AdminUserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = "__all__"


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    inlines = [ProfileInline]

    list_display = ("phone", "full_name", "email", "role", "is_active", "email_verified", "date_joined")
    list_filter = ("role", "is_active", "email_verified", "is_superuser", "date_joined")
    search_fields = ("phone", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login", "email_verified_at")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "email", "email_verified", "email_verified_at")}),
        ("نقش و دسترسی", {"fields": ("role", "is_active", "is_superuser", "groups", "user_permissions")}),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "email", "first_name", "last_name", "role", "password1", "password2"),
            },
        ),
    )

    @admin.display(description="نام")
    def full_name(self, obj):
        return obj.get_full_name() or "—"
