from django.urls import path

from .views import custody_index

app_name = "custody"

urlpatterns = [
    path("", custody_index, name="custody_index"),
]
