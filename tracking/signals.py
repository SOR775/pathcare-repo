from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from .models import Notification, Order

User = get_user_model()


def _broadcast_to_user(user_id, message_type, payload):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "notification.event",
            "payload": {
                "message_type": message_type,
                **payload,
            },
        },
    )


def _order_watchers(order):
    user_ids = set()

    if order.carrier and order.carrier.user_id:
        user_ids.add(order.carrier.user_id)

    if order.client and order.client.contact_email:
        client_user = User.objects.filter(email=order.client.contact_email).first()
        if client_user:
            user_ids.add(client_user.pk)

    user_ids.update(
        User.objects.filter(role__in=[User.Role.SUPER_ADMIN, User.Role.DISPATCHER], is_active=True)
        .values_list('pk', flat=True)
    )

    if order.status in [Order.Status.DELIVERED, Order.Status.RECEIVED, Order.Status.COMPLETED]:
        user_ids.update(
            User.objects.filter(role=User.Role.LAB_STAFF, is_active=True).values_list('pk', flat=True)
        )

    return list(user_ids)


def _notification_payload(notification):
    return {
        "pk": str(notification.pk),
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at_seconds": int((timezone.now() - notification.created_at).total_seconds()),
        "mark_url": reverse("tracking:notification_mark_read", args=[notification.pk]),
    }


@receiver(post_save, sender=Notification)
def on_notification_created(sender, instance, created, **kwargs):
    if not created:
        return

    payload = {
        "notification": _notification_payload(instance),
        "unread": Notification.objects.filter(user=instance.user, is_read=False).count(),
    }
    _broadcast_to_user(instance.user_id, "notification.new", payload)


def broadcast_order_update(order, user_ids=None):
    if user_ids is None:
        user_ids = _order_watchers(order)
    if not user_ids:
        return

    payload = {
        "order_id": str(order.pk),
        "status": order.status,
        "reference_code": order.reference_code,
    }
    for uid in user_ids:
        _broadcast_to_user(uid, "order.update", payload)
