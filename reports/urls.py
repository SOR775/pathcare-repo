from django.urls import path

from .views import report_index

app_name = "reports"

urlpatterns = [
    path("", report_index, name="report_index"),
]
