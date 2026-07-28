from django.urls import path

from .views import core_index

app_name = "core"

urlpatterns = [
    path("", core_index, name="core_index"),
]
