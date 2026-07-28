from django.urls import path

from .views import notification_index

app_name = "notifications"

urlpatterns = [
    path("", notification_index, name="notification_index"),
]
