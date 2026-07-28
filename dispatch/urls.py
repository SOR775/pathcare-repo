from django.urls import path

from .views import dispatch_index

app_name = "dispatch"

urlpatterns = [
    path("", dispatch_index, name="dispatch_index"),
]
