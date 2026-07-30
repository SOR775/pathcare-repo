from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Carrier, Client, CustodyEvent, Order


class CarrierAssignmentTests(TestCase):
    def test_dispatcher_cannot_assign_busy_carrier(self):
        dispatcher = get_user_model().objects.create_user(
            username="dispatcher-busy",
            password="secret123",
            role="dispatcher",
        )
        carrier = Carrier.objects.create(phone="0755555555", status=Carrier.Status.ON_JOB)
        client = Client.objects.create(name="Busy Clinic", contact_phone="0712345678", address="Nairobi")
        active_order = Order.objects.create(client=client, carrier=carrier, status=Order.Status.IN_TRANSIT, priority=Order.Priority.ROUTINE)
        new_order = Order.objects.create(client=client, priority=Order.Priority.URGENT)

        self.client.login(username="dispatcher-busy", password="secret123")
        response = self.client.post(
            reverse("tracking:order_assign_carrier", kwargs={"pk": new_order.pk}),
            {"carrier": carrier.pk},
            follow=True,
        )

        new_order.refresh_from_db()
        carrier.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carrier already has an active job")
        self.assertIsNone(new_order.carrier)
        self.assertEqual(carrier.status, Carrier.Status.ON_JOB)

    def test_carrier_becomes_available_only_on_complete(self):
        dispatcher = get_user_model().objects.create_user(
            username="dispatcher-complete",
            password="secret123",
            role="dispatcher",
        )
        client = Client.objects.create(name="Complete Clinic", contact_phone="0712345678", address="Nairobi")
        carrier = Carrier.objects.create(phone="0755555555", status=Carrier.Status.AVAILABLE)
        order = Order.objects.create(client=client, priority=Order.Priority.URGENT)

        self.client.login(username="dispatcher-complete", password="secret123")
        self.client.post(
            reverse("tracking:order_assign_carrier", kwargs={"pk": order.pk}),
            {"carrier": carrier.pk},
            follow=True,
        )
        order.refresh_from_db()
        carrier.refresh_from_db()
        self.assertEqual(order.status, Order.Status.ASSIGNED)
        self.assertEqual(carrier.status, Carrier.Status.ON_JOB)

        # Carrier should become available once the order is delivered
        self.client.post(reverse("tracking:order_mark_delivery", kwargs={"pk": order.pk}), follow=True)
        order.refresh_from_db()
        carrier.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)
        self.assertEqual(carrier.status, Carrier.Status.AVAILABLE)

        self.client.post(reverse("tracking:order_mark_received", kwargs={"pk": order.pk}), follow=True)
        order.refresh_from_db()
        carrier.refresh_from_db()
        self.assertEqual(order.status, Order.Status.RECEIVED)
        self.assertEqual(carrier.status, Carrier.Status.AVAILABLE)

        self.client.post(reverse("tracking:order_mark_complete", kwargs={"pk": order.pk}), follow=True)
        order.refresh_from_db()
        carrier.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertEqual(carrier.status, Carrier.Status.AVAILABLE)

    def test_cannot_reassign_order_once_assigned(self):
        dispatcher = get_user_model().objects.create_user(
            username="dispatcher-reassign",
            password="secret123",
            role="dispatcher",
        )
        client = Client.objects.create(name="Reassign Clinic", contact_phone="0712345678", address="Nairobi")
        carrier1 = Carrier.objects.create(phone="0755555555", status=Carrier.Status.AVAILABLE)
        carrier2 = Carrier.objects.create(phone="0766666666", status=Carrier.Status.AVAILABLE)
        order = Order.objects.create(client=client, priority=Order.Priority.URGENT)

        self.client.login(username="dispatcher-reassign", password="secret123")
        self.client.post(
            reverse("tracking:order_assign_carrier", kwargs={"pk": order.pk}),
            {"carrier": carrier1.pk},
            follow=True,
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.ASSIGNED)
        self.assertEqual(order.carrier, carrier1)

        response = self.client.post(
            reverse("tracking:order_assign_carrier", kwargs={"pk": order.pk}),
            {"carrier": carrier2.pk},
            follow=True,
        )
        order.refresh_from_db()
        response_content = response.content.decode()

        self.assertEqual(order.carrier, carrier1)
        self.assertEqual(order.status, Order.Status.ASSIGNED)
        self.assertContains(response, "Order cannot be assigned because it is already assigned or in progress.")
        self.assertNotIn(str(carrier2.pk), response_content)

    def test_auto_assign_does_not_reassign_already_assigned_order(self):
        dispatcher = get_user_model().objects.create_user(
            username="dispatcher-auto-reassign",
            password="secret123",
            role="dispatcher",
        )
        client = Client.objects.create(name="Auto Reassign Clinic", contact_phone="0712345678", address="Nairobi")
        carrier1 = Carrier.objects.create(phone="0755555555", status=Carrier.Status.AVAILABLE)
        carrier2 = Carrier.objects.create(phone="0766666666", status=Carrier.Status.AVAILABLE)
        order = Order.objects.create(client=client, priority=Order.Priority.URGENT)

        self.client.login(username="dispatcher-auto-reassign", password="secret123")
        self.client.post(
            reverse("tracking:order_assign_carrier", kwargs={"pk": order.pk}),
            {"carrier": carrier1.pk},
            follow=True,
        )
        order.refresh_from_db()
        self.assertEqual(order.carrier, carrier1)

        response = self.client.post(
            reverse("tracking:order_auto_assign", kwargs={"pk": order.pk}),
            follow=True,
        )
        order.refresh_from_db()

        self.assertEqual(order.carrier, carrier1)
        self.assertEqual(order.status, Order.Status.ASSIGNED)
        self.assertContains(response, "Order cannot be assigned because it is already assigned or in progress.")
    
