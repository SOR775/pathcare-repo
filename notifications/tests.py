from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import NotificationLog


class NotificationLogTests(TestCase):
    def test_notification_log_can_be_created(self):
        user = get_user_model().objects.create_user(username="notify", password="secret")

        log = NotificationLog.objects.create(recipient=user, message="Pickup confirmed")

        self.assertEqual(log.recipient.username, "notify")
        self.assertEqual(log.message, "Pickup confirmed")
