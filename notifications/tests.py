from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from tracking.models import Notification

from .models import NotificationLog


class NotificationLogTests(TestCase):
    def test_notification_log_can_be_created(self):
        user = get_user_model().objects.create_user(username="notify", password="secret")

        log = NotificationLog.objects.create(recipient=user, message="Pickup confirmed")

        self.assertEqual(log.recipient.username, "notify")
        self.assertEqual(log.message, "Pickup confirmed")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_notification_creation_sends_email_to_user(self):
        user = get_user_model().objects.create_user(
            username="notify-email",
            email="notify@example.com",
            password="secret",
        )

        Notification.objects.create(user=user, message="Pickup confirmed")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["notify@example.com"])
        self.assertIn("Pickup confirmed", mail.outbox[0].body)
        self.assertTrue(
            NotificationLog.objects.filter(recipient=user, channel=NotificationLog.Channel.EMAIL).exists()
        )
