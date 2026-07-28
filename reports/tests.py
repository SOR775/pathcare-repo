from django.test import TestCase
from django.urls import reverse

from tracking.models import Client, Order

from .models import ReportSnapshot


class ReportSnapshotTests(TestCase):
    def test_report_snapshot_can_be_created(self):
        snapshot = ReportSnapshot.objects.create(title="Daily Summary", summary="All clear")

        self.assertEqual(snapshot.title, "Daily Summary")
        self.assertEqual(snapshot.summary, "All clear")


class ReportIndexViewTests(TestCase):
    def test_report_index_displays_summary_metrics(self):
        client = Client.objects.create(name="Nairobi Lab", contact_phone="0712345678", address="Nairobi")
        Order.objects.create(reference_code="ORD-1001", client=client, status=Order.Status.PENDING)
        Order.objects.create(reference_code="ORD-1002", client=client, status=Order.Status.DELIVERED)

        response = self.client.get(reverse("reports:report_index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operational report overview")
        self.assertContains(response, "Pending")
        self.assertContains(response, "Delivered")
        self.assertContains(response, "ORD-1001")

    def test_report_index_can_filter_orders_by_status(self):
        client = Client.objects.create(name="Nairobi Lab", contact_phone="0712345678", address="Nairobi")
        Order.objects.create(reference_code="ORD-1001", client=client, status=Order.Status.PENDING)
        Order.objects.create(reference_code="ORD-1002", client=client, status=Order.Status.DELIVERED)

        response = self.client.get(reverse("reports:report_index"), {"status": Order.Status.DELIVERED})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["orders"]), list(Order.objects.filter(status=Order.Status.DELIVERED)))

    def test_report_index_can_export_orders_as_csv(self):
        client = Client.objects.create(name="Nairobi Lab", contact_phone="0712345678", address="Nairobi")
        Order.objects.create(reference_code="ORD-1001", client=client, status=Order.Status.PENDING)

        response = self.client.get(reverse("reports:report_index"), {"download": "csv"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertContains(response, "reference_code")
        self.assertContains(response, "ORD-1001")
