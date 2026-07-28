from django.urls import path

from .views import sample_index

app_name = "samples"

urlpatterns = [
    path("", sample_index, name="sample_index"),
]
