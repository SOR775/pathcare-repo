from django.urls import re_path
from tracking.consumers import PathcareConsumer

websocket_urlpatterns = [
    re_path(r"ws/notifications/$", PathcareConsumer.as_asgi()),
    re_path(r"ws/pathcare/$", PathcareConsumer.as_asgi()),
]
