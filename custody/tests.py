from django.test import TestCase

from tracking.models import Client, Order
from .models import CustodyCheckpoint


class CustodyCheckpointTests(TestCase):
    def test_custody_checkpoint_can_be_created(self):
        client = Client.objects.create(
            name="Custody Lab",
            contact_phone="555-0140",
            address="101 Secure Route",
        )
        order = Order.objects.create(client=client, reference_code="ORD-3003")

        checkpoint = CustodyCheckpoint.objects.create(order=order, checkpoint_name="Packed")

        self.assertEqual(checkpoint.order.reference_code, "ORD-3003")
        self.assertEqual(checkpoint.checkpoint_name, "Packed")
