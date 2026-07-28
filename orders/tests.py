from django.test import TestCase

from tracking.models import Client, Order
from .models import OrderWorkflow


class OrderWorkflowTests(TestCase):
    def test_order_workflow_can_be_created(self):
        client = Client.objects.create(
            name="Lab Client",
            contact_phone="555-0120",
            address="456 Test Avenue",
        )
        order = Order.objects.create(client=client, reference_code="ORD-1001")

        workflow = OrderWorkflow.objects.create(order=order, handoff_window_minutes=15)

        self.assertEqual(workflow.order.reference_code, "ORD-1001")
        self.assertEqual(workflow.handoff_window_minutes, 15)
