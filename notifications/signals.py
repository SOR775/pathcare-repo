from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from tracking.models import Notification as TrackingNotification

from .models import NotificationLog


@receiver(post_save, sender=TrackingNotification)
def deliver_notification_email(sender, instance, created, **kwargs):
    if not created:
        return

    user = instance.user
    if not getattr(user, "email", None):
        return

    subject = "PathCare notification"
    message = instance.message or "You have a new PathCare notification."
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )

    NotificationLog.objects.create(
        recipient=user,
        channel=NotificationLog.Channel.EMAIL,
        message=message,
    )
