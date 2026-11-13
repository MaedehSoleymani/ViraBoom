from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),  # [ACCOUNTS]
    # صفحه اصلی موقت — نفر دوم (Catalog) جایگزینش می‌کند؛ فقط name="home" حفظ شود.
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
