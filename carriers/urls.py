from django.urls import path

from .views import carrier_index

app_name = "carriers"

urlpatterns = [
    path("", carrier_index, name="carrier_index"),
]
