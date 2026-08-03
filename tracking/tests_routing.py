from django.conf import settings
from django.test import SimpleTestCase

from pathcare.routing import websocket_urlpatterns


class WebsocketRoutingTests(SimpleTestCase):
    def test_project_routing_includes_tracking_pathcare_route(self):
        regexes = []
        for pattern in websocket_urlpatterns:
            pattern_obj = getattr(pattern, "pattern", None)
            if pattern_obj is not None and hasattr(pattern_obj, "regex"):
                regexes.append(pattern_obj.regex.pattern)
            else:
                regexes.append(str(pattern))

        self.assertTrue(any("ws/pathcare/" in regex for regex in regexes))
        self.assertTrue(any("ws/notifications/" in regex for regex in regexes))

    def test_default_channel_layer_is_configured_for_local_development(self):
        self.assertIn("default", settings.CHANNEL_LAYERS)
        self.assertEqual(
            settings.CHANNEL_LAYERS["default"]["BACKEND"],
            "channels.layers.InMemoryChannelLayer",
        )

    def test_local_development_does_not_force_https_redirect(self):
        self.assertFalse(settings.SECURE_SSL_REDIRECT)
