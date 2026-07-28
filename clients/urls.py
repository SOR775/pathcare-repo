from django.urls import path

from .views import client_index

app_name = "clients"

urlpatterns = [
    path("", client_index, name="client_index"),
]
