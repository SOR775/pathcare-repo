from django.conf import settings
from django.db import models


class NotificationLog(models.Model):
    """Record of notifications sent for operational events."""

    class Channel(models.TextChoices):
        SMS = "sms", "SMS"
        EMAIL = "email", "Email"
        PUSH = "push", "Push"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_logs",
    )
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.EMAIL)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.channel}: {self.message[:40]}"
