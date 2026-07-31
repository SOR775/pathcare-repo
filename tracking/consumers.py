# import json
# from channels.generic.websocket import AsyncJsonWebsocketConsumer
# from channels.db import database_sync_to_async
# from django.contrib.auth.models import AnonymousUser


# class PathcareConsumer(AsyncJsonWebsocketConsumer):
#     async def connect(self):
#         user = self.scope.get("user")
#         if user is None or isinstance(user, AnonymousUser) or not user.is_authenticated:
#             await self.close(code=4001)
#             return

#         self.user = user
#         self.group_name = f"user_{user.pk}"
#         await self.channel_layer.group_add(self.group_name, self.channel_name)
#         await self.accept()

#     async def disconnect(self, close_code):
#         if hasattr(self, "group_name"):
#             await self.channel_layer.group_discard(self.group_name, self.channel_name)

#     async def receive_json(self, content, **kwargs):
#         # no client-to-server commands are required for current functionality
#         pass

#     async def notification_event(self, event):
#         payload = event.get("payload", {}) or {}
#         await self.send_json({
#             "type": payload.get("message_type", event.get("type")),
#             "payload": payload,
#         })


import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser


CARRIER_GROUP = "carrier_positions"


class PathcareConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.user = user
        self.user_group = f"user_{user.pk}"

        # ── Personal notification group (always) ──
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        # ── Carrier monitoring group (admin / dispatcher only) ──
        role = await self.get_user_role()
        if role in ("super_admin", "dispatcher"):
            await self.channel_layer.group_add(CARRIER_GROUP, self.channel_name)

        await self.accept()

        # Send initial carrier snapshot to admin users
        if role in ("super_admin", "dispatcher"):
            carriers = await self.get_carrier_snapshot()
            await self.send_json({
                "type": "carrier_snapshot",
                "carriers": carriers,
            })

    async def disconnect(self, close_code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
        if hasattr(self, "user"):
            await self.channel_layer.group_discard(CARRIER_GROUP, self.channel_name)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get("type", "")

        if msg_type == "subscribe_carriers":
            carriers = await self.get_carrier_snapshot()
            await self.send_json({
                "type": "carrier_snapshot",
                "carriers": carriers,
            })

    # ── Personal notification handler ──
    async def notification_event(self, event):
        payload = event.get("payload", {}) or {}
        await self.send_json({
            "type": payload.get("message_type", event.get("type")),
            "payload": payload,
        })

    # ── Carrier position broadcast handler ──
    async def carrier_update(self, event):
        """
        Receives broadcast from backend when a carrier's position changes.
        Event shape: { "type": "carrier_update", "carriers": [...] }
        """
        await self.send_json({
            "type": "carrier_update",
            "carriers": event.get("carriers", []),
        })

    # ── Database helpers ──
    @database_sync_to_async
    def get_user_role(self):
        try:
            return self.user.profile.role if hasattr(self.user, "profile") else None
        except Exception:
            return None

    @database_sync_to_async
    def get_carrier_snapshot(self):
        """
        Return current state of all active carriers.
        MUST match the same shape as the carrier_positions JSON view.
        """
        try:
            from tracking.models import Carrier, Order
            carriers = Carrier.objects.filter(is_active=True).select_related("user")
            result = []
            for c in carriers:
                name = "Unnamed carrier"
                if c.user:
                    name = c.user.get_full_name() or c.user.username

                order = Order.objects.filter(
                    carrier=c,
                    status__in=[
                        Order.Status.ASSIGNED, Order.Status.ACCEPTED,
                        Order.Status.EN_ROUTE_TO_CLIENT, Order.Status.AT_CLIENT,
                        Order.Status.PICKED_UP, Order.Status.IN_TRANSIT,
                        Order.Status.DELIVERED,
                    ],
                ).order_by("-created_at").first()

                result.append({
                    "id": str(c.id),
                    "name": name,
                    "latitude": c.current_latitude,
                    "longitude": c.current_longitude,
                    "last_location_update": (
                        c.last_location_update.isoformat() if c.last_location_update else None
                    ),
                    "status": c.get_status_display(),
                    "order": order.reference_code if order else None,
                    "order_status": order.get_status_display() if order else None,
                })
            return result
        except Exception:
            return []


# ═══════════════════════════════════════════
# BROADCAST HELPER — call this from views/models
# ═══════════════════════════════════════════

def broadcast_carrier_positions(carriers_data):
    """
    Push updated carrier positions to all connected admin/dispatcher browsers.

    Usage from any Django view:
        from tracking.consumers import broadcast_carrier_positions
        carriers = serialize_carrier_positions(Carrier.objects.filter(is_active=True))
        broadcast_carrier_positions(carriers)
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        CARRIER_GROUP,
        {
            "type": "carrier_update",
            "carriers": carriers_data,
        },
    )


def broadcast_notification(user_id, payload):
    """
    Send a notification to a specific user's open browser tabs.

    Usage:
        broadcast_notification(user.pk, {
            "message_type": "order_assigned",
            "order_id": order.pk,
            "message": f"Order {order.reference_code} assigned to you",
        })
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "notification_event",
            "payload": payload,
        },
    )
