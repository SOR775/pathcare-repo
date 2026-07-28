from django.contrib import admin
from django.urls import include, path

from accounts.views import login_view, logout_view, password_reset_view
from .pwa_views import offline_view, manifest_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("offline.html", offline_view, name="offline"),
    path("manifest.json", manifest_view, name="manifest"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("password-reset/", password_reset_view, name="password_reset"),
    path("accounts/", include("accounts.urls")),
    path("client-portal/", include("clients.urls")),
    path("carrier-assignments/", include("carriers.urls")),
    path("orders/", include("orders.urls")),
    path("samples/", include("samples.urls")),
    path("custody/", include("custody.urls")),
    path("dispatch/", include("dispatch.urls")),
    path("notifications/", include("notifications.urls")),
    path("reports/", include("reports.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("core/", include("core.urls")),
    path("", include("tracking.urls")),
]
