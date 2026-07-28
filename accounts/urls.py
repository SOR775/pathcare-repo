from django.urls import path

from django.urls import path

from .views import (
    account_index,
    login_view,
    logout_view,
    password_reset_view,
    role_redirect,
    user_management,
    user_edit,
    user_toggle_active,
    user_delete,
)

app_name = "accounts"

urlpatterns = [
    path("", account_index, name="account_index"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("role-redirect/", role_redirect, name="role_redirect"),
    path("password-reset/", password_reset_view, name="password_reset"),
    path("users/", user_management, name="user_management"),
    path("users/<int:pk>/edit/", user_edit, name="user_edit"),
    path("users/<int:pk>/toggle-active/", user_toggle_active, name="user_toggle_active"),
    path("users/<int:pk>/delete/", user_delete, name="user_delete"),
]
