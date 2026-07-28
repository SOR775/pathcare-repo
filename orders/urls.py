from django.urls import path

from .views import order_index

app_name = "orders"

urlpatterns = [
    path("", order_index, name="order_index"),
]
