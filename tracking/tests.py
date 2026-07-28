from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from .models import Carrier, Client, Order, Sample, Notification, CustodyEvent


class DashboardWorkflowViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="dispatch",
            password="secret123",
        )

    def test_dashboard_displays_dispatch_overview(self):
        self.client.login(username="dispatch", password="secret123")

        response = self.client.get(reverse("tracking:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operational overview")
        self.assertContains(response, "Dispatch queue")
        self.assertContains(response, "Carrier availability")

    def test_dashboard_shows_super_admin_for_superuser(self):
        superuser = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="secret123",
        )
        self.client.login(username="admin", password="secret123")

        response = self.client.get(reverse("tracking:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Signed in as Super Admin")

    def test_order_detail_shows_assignment_and_status_context(self):
        client = Client.objects.create(
            name="Test Clinic",
            contact_phone="0712345678",
            address="Nairobi",
        )
        carrier_user = get_user_model().objects.create_user(
            username="carrier-user",
            password="secret123",
            role=get_user_model().Role.CARRIER,
            phone="0712345678",
        )
        carrier = carrier_user.carrier_profile
        order = Order.objects.create(
            client=client,
            priority=Order.Priority.URGENT,
            carrier=carrier,
            status=Order.Status.ACCEPTED,
            latitude=1.2921,
            longitude=36.8219,
        )

        self.client.login(username="carrier-user", password="secret123")
        response = self.client.get(reverse("tracking:order_detail", kwargs={"pk": order.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Order overview")
        self.assertContains(response, order.reference_code)
        self.assertContains(response, "View route in app")

    def test_dashboard_handles_order_with_carrier_missing_user(self):
        client = Client.objects.create(
            name="Test Clinic",
            contact_phone="0712345678",
            address="Nairobi",
        )
        carrier = Carrier.objects.create(phone="0712345678")
        Order.objects.create(client=client, carrier=carrier, priority=Order.Priority.URGENT)

        self.client.login(username="dispatch", password="secret123")
        response = self.client.get(reverse("tracking:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unnamed carrier")

    def test_carrier_dashboard_shows_live_navigation_for_pinned_order(self):
        user = get_user_model().objects.create_user(
            username="carrier-list",
            password="secret123",
            role=get_user_model().Role.CARRIER,
            phone="0712345678",
        )
        carrier = user.carrier_profile
        client = Client.objects.create(
            name="Field Clinic",
            contact_phone="0712345678",
            address="Nairobi",
        )
        Order.objects.create(
            client=client,
            carrier=carrier,
            priority=Order.Priority.URGENT,
            status=Order.Status.ASSIGNED,
            latitude=-1.2921,
            longitude=36.8219,
        )

        self.client.login(username="carrier-list", password="secret123")
        response = self.client.get(reverse("tracking:carrier_view"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View route inside app")
        self.assertContains(response, "#carrier-route-map")
        self.assertContains(response, "Route guidance")
        self.assertContains(response, "Open in maps")
        self.assertContains(response, "Start live tracking")
        self.assertContains(response, "navigator.geolocation")
        self.assertContains(response, "Fastest route")

    def test_carrier_dashboard_routes_to_lab_after_pickup_collection(self):
        user = get_user_model().objects.create_user(
            username="carrier-lab-route",
            password="secret123",
            role=get_user_model().Role.CARRIER,
            phone="0712345678",
        )
        carrier = user.carrier_profile
        client = Client.objects.create(
            name="Lab Route Client",
            contact_phone="0712345678",
            address="Nairobi",
        )
        Order.objects.create(
            client=client,
            carrier=carrier,
            priority=Order.Priority.URGENT,
            status=Order.Status.PICKED_UP,
            latitude=-1.2921,
            longitude=36.8219,
        )

        self.client.login(username="carrier-lab-route", password="secret123")
        response = self.client.get(reverse("tracking:carrier_view"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Route to lab")
        self.assertContains(response, "lab-location")

    def test_dashboard_renders_for_client_user(self):
        client_user = get_user_model().objects.create_user(
            username="client-user",
            email="client@example.com",
            password="secret123",
            first_name="Client",
            last_name="User",
        )
        client = Client.objects.create(
            name="Client User Clinic",
            contact_name="Client User",
            contact_phone="0712345678",
            contact_email="client@example.com",
            address="Nairobi",
        )
        Order.objects.create(client=client, priority=Order.Priority.URGENT)

        self.client.login(username="client-user", password="secret123")
        response = self.client.get(reverse("tracking:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Client User Clinic")

    def test_client_list_page_renders_full_client_form(self):
        self.client.login(username="dispatch", password="secret123")

        response = self.client.get(reverse("tracking:client_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="contact_phone"')
        self.assertContains(response, 'name="address"')

    def test_client_create_route_renders_client_form_for_dashboard_access(self):
        self.client.login(username="dispatch", password="secret123")

        response = self.client.get(reverse("tracking:client_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="contact_phone"')
        self.assertContains(response, 'name="address"')

    def test_client_can_submit_pickup_request(self):
        client_user = get_user_model().objects.create_user(
            username="client-requestor",
            email="requestor@example.com",
            password="secret123",
            first_name="Client",
            last_name="Requester",
            role="client",
        )
        self.client.login(username="client-requestor", password="secret123")

        response = self.client.post(
            reverse("tracking:client_request_pickup"),
            {
                "pickup_location": "Nairobi Hospital",
                "contact_person": "Jane Doe",
                "contact_phone": "0712345678",
                "requested_pickup_time": "2026-07-24T09:30",
                "sample_type": "blood",
                "sample_count": 2,
                "temperature_requirement": "refrigerated",
                "priority": Order.Priority.URGENT,
                "notes": "Please handle carefully.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        order = Order.objects.latest("created_at")
        self.assertEqual(order.client.name, "Jane Doe")
        self.assertEqual(order.priority, Order.Priority.URGENT)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.samples.count(), 2)
        self.assertTrue(order.custody_events.filter(event_type="order_created").exists())

    def test_order_detail_page_renders_available_carriers_for_assignment(self):
        dispatcher = get_user_model().objects.create_user(
            username="dispatcher-assigner",
            password="secret123",
            role="dispatcher",
        )
        client = Client.objects.create(name="Flow Clinic", contact_phone="0712345678", address="Nairobi")
        order = Order.objects.create(client=client, priority=Order.Priority.URGENT)
        carrier = Carrier.objects.create(phone="0755555555", status=Carrier.Status.AVAILABLE)

        self.client.login(username="dispatcher-assigner", password="secret123")
        response = self.client.get(reverse("tracking:order_detail", kwargs={"pk": order.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="carrier"')
        self.assertContains(response, str(carrier))

    def test_carrier_can_open_assigned_order_detail(self):
        carrier_user = get_user_model().objects.create_user(
            username="carrier-viewer",
            password="secret123",
            role="carrier",
        )
        carrier = carrier_user.carrier_profile
        client = Client.objects.create(name="Carrier Client", contact_phone="0712345678", address="Nairobi")
        order = Order.objects.create(client=client, carrier=carrier, priority=Order.Priority.URGENT)

        self.client.login(username="carrier-viewer", password="secret123")
        response = self.client.get(reverse("tracking:order_detail", kwargs={"pk": order.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accept assignment")

    def test_order_detail_shows_embedded_map_for_pinned_location(self):
        dispatcher = get_user_model().objects.create_user(
            username="dispatcher-map",
            password="secret123",
            role="dispatcher",
        )
        client = Client.objects.create(name="Map Client", contact_phone="0712345678", address="Nairobi")
        order = Order.objects.create(
            client=client,
            priority=Order.Priority.URGENT,
            latitude=-1.2921,
            longitude=36.8219,
        )

        self.client.login(username="dispatcher-map", password="secret123")
        response = self.client.get(reverse("tracking:order_detail", kwargs={"pk": order.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="order-map"')
        self.assertContains(response, 'L.map("order-map")')

    def test_order_detail_renders_carrier_route_to_pickup_when_location_is_available(self):
        carrier_user = get_user_model().objects.create_user(
            username="carrier-route",
            password="secret123",
            role=get_user_model().Role.CARRIER,
            phone="0712345678",
        )
        carrier = carrier_user.carrier_profile
        carrier.current_latitude = -1.3000
        carrier.current_longitude = 36.8000
        carrier.save()
        client = Client.objects.create(name="Route Client", contact_phone="0712345678", address="Nairobi")
        order = Order.objects.create(
            client=client,
            carrier=carrier,
            priority=Order.Priority.URGENT,
            status=Order.Status.ACCEPTED,
            latitude=-1.2921,
            longitude=36.8219,
        )

        self.client.login(username="carrier-route", password="secret123")
        response = self.client.get(reverse("tracking:order_detail", kwargs={"pk": order.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-carrier-lat="-1.3"')
        self.assertContains(response, 'data-carrier-lng="36.8"')
        self.assertContains(response, 'L.polyline(')

    def test_carrier_can_progress_through_trip_workflow(self):
        carrier_user = get_user_model().objects.create_user(
            username="carrier-progress",
            password="secret123",
            role="carrier",
        )
        carrier = carrier_user.carrier_profile
        client = Client.objects.create(name="Pickup Client", contact_phone="0712345678", address="Nairobi")
        order = Order.objects.create(client=client, carrier=carrier, priority=Order.Priority.URGENT, status=Order.Status.ASSIGNED)

        self.client.login(username="carrier-progress", password="secret123")
        response = self.client.post(reverse("tracking:order_accept_assignment", kwargs={"pk": order.pk}), follow=True)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.ACCEPTED)
        self.assertContains(response, "assignment accepted")

        response = self.client.post(reverse("tracking:order_start_to_client", kwargs={"pk": order.pk}), follow=True)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.EN_ROUTE_TO_CLIENT)
        self.assertContains(response, "en route to client")
        self.assertContains(response, "Carrier dashboard")

        response = self.client.post(reverse("tracking:order_arrive_client", kwargs={"pk": order.pk}), follow=True)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.AT_CLIENT)
        self.assertContains(response, "arrived at client")

        response = self.client.post(reverse("tracking:order_mark_pickup", kwargs={"pk": order.pk}), follow=True)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PICKED_UP)
        self.assertTrue(order.custody_events.filter(event_type="picked_up").exists())

        response = self.client.post(reverse("tracking:order_mark_in_transit", kwargs={"pk": order.pk}), follow=True)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.IN_TRANSIT)
        self.assertContains(response, "marked in transit")

        response = self.client.post(reverse("tracking:order_mark_delivery", kwargs={"pk": order.pk}), follow=True)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)
        self.assertTrue(order.custody_events.filter(event_type="delivered").exists())

    def test_carrier_can_verify_sample_barcodes_at_pickup(self):
        carrier_user = get_user_model().objects.create_user(
            username="carrier-scan",
            password="secret123",
            role="carrier",
        )
        carrier = carrier_user.carrier_profile
        client = Client.objects.create(name="Scan Client", contact_phone="0712345678", address="Nairobi")
        order = Order.objects.create(client=client, carrier=carrier, priority=Order.Priority.URGENT)
        s1 = Sample.objects.create(order=order, barcode=f"{order.reference_code}-1", sample_type=Sample.SampleType.BLOOD)
        s2 = Sample.objects.create(order=order, barcode=f"{order.reference_code}-2", sample_type=Sample.SampleType.BLOOD)

        self.client.login(username="carrier-scan", password="secret123")
        # Carrier posts barcodes
        resp = self.client.post(
            reverse("tracking:verify_samples_collection", kwargs={"pk": order.pk}),
            {"barcodes": f"{s1.barcode}\n{s2.barcode}"},
            follow=True,
        )

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PICKED_UP)
        self.assertTrue(order.custody_events.filter(event_type=CustodyEvent.EventType.PICKED_UP).exists())

    def test_custody_event_string_handles_missing_sample(self):
        client = Client.objects.create(name="Audit Client", contact_phone="0712345678", address="Nairobi")
        order = Order.objects.create(client=client, priority=Order.Priority.URGENT)
        event = CustodyEvent.objects.create(order=order, event_type=CustodyEvent.EventType.ORDER_CREATED)

        self.assertIn("Order created", str(event))
        self.assertIn("no sample", str(event))

    def test_staff_user_with_order_delete_permission_can_delete_order_with_custody_events(self):
        user = get_user_model().objects.create_user(
            username="order-deleter",
            password="secret123",
            is_staff=True,
        )
        order_content_type = ContentType.objects.get(app_label="tracking", model="order")
        user.user_permissions.add(Permission.objects.get(content_type=order_content_type, codename="delete_order"))
        user.user_permissions.add(Permission.objects.get(content_type=order_content_type, codename="view_order"))
        user.user_permissions.add(Permission.objects.get(content_type=order_content_type, codename="change_order"))
        self.client.force_login(user)

        client = Client.objects.create(name="Delete Client", contact_phone="0712345678", address="Nairobi")
        order = Order.objects.create(client=client, priority=Order.Priority.URGENT)
        CustodyEvent.objects.create(order=order, event_type=CustodyEvent.EventType.ORDER_CREATED)

        response = self.client.post(reverse("admin:tracking_order_delete", args=[order.pk]), {"post": "yes"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())

    def test_custody_event_remains_after_order_deletion(self):
        client = Client.objects.create(name="Audit Client", contact_phone="0712345678", address="Nairobi")
        order = Order.objects.create(client=client, priority=Order.Priority.URGENT)
        event = CustodyEvent.objects.create(order=order, event_type=CustodyEvent.EventType.ORDER_CREATED)

        order.delete()
        event.refresh_from_db()

        self.assertIsNone(event.order)
        self.assertTrue(CustodyEvent.objects.filter(pk=event.pk).exists())

    def test_sample_can_survive_order_deletion(self):
        client = Client.objects.create(name="Sample Client", contact_phone="0712345678", address="Nairobi")
        order = Order.objects.create(client=client, priority=Order.Priority.URGENT)
        sample = Sample.objects.create(order=order, barcode="SAMPLE-001", sample_type=Sample.SampleType.BLOOD)

        order.delete()
        sample.refresh_from_db()

        self.assertIsNone(sample.order)
        self.assertTrue(Sample.objects.filter(pk=sample.pk).exists())

    def test_notifications_created_on_assign_and_delivery(self):
        dispatcher = get_user_model().objects.create_user(
            username="dispatcher-notify",
            password="secret123",
            role="dispatcher",
        )
        client_user = get_user_model().objects.create_user(
            username="client-notify",
            email="client-notify@example.com",
            password="secret123",
            role="client",
        )
        carrier_user = get_user_model().objects.create_user(
            username="carrier-notify",
            password="secret123",
            role="carrier",
        )

        carrier = carrier_user.carrier_profile
        client = Client.objects.create(name="Notify Client", contact_phone="0712345678", address="Nairobi", contact_email="client-notify@example.com")
        order = Order.objects.create(client=client, priority=Order.Priority.URGENT)

        # assign the carrier to the order so delivery can be confirmed
        order.carrier = carrier
        order.status = Order.Status.IN_TRANSIT
        order.save()

        # dispatcher assigns carrier
        self.client.login(username="dispatcher-notify", password="secret123")
        response = self.client.post(
            reverse("tracking:order_assign_carrier", kwargs={"pk": order.pk}),
            {"carrier": carrier.pk},
            follow=True,
        )

        # carrier user should have a notification
        self.assertTrue(Notification.objects.filter(user=carrier_user, order=order, message__icontains="assigned").exists())

        # set delivery state after successful assignment
        order.refresh_from_db()
        order.status = Order.Status.IN_TRANSIT
        order.save()

        self.client.login(username="carrier-notify", password="secret123")
        response = self.client.post(reverse("tracking:order_mark_delivery", kwargs={"pk": order.pk}), follow=True)

        # client user should have a delivery notification
        self.assertTrue(Notification.objects.filter(user=client_user, order=order, message__icontains="delivered").exists())

    def test_client_can_view_their_order_detail(self):
        client_user = get_user_model().objects.create_user(
            username="client-viewer",
            email="client-viewer@example.com",
            password="secret123",
            first_name="Client",
            last_name="Viewer",
            role="client",
        )
        client = Client.objects.create(
            name="Client Viewer",
            contact_name="Client Viewer",
            contact_phone="0712345678",
            contact_email="client-viewer@example.com",
            address="Nairobi",
        )
        order = Order.objects.create(client=client, priority=Order.Priority.URGENT)

        self.client.login(username="client-viewer", password="secret123")
        response = self.client.get(reverse("tracking:order_detail", kwargs={"pk": order.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.reference_code)
        self.assertContains(response, "Order overview")

    def test_lab_staff_lands_on_lab_dashboard_and_confirms_receipt(self):
        lab_user = get_user_model().objects.create_user(
            username="lab-staff",
            email="lab@example.com",
            password="secret123",
            role="lab_staff",
        )
        client = Client.objects.create(
            name="Lab Client",
            contact_phone="0712345678",
            address="Nairobi",
        )
        carrier_user = get_user_model().objects.create_user(
            username="carrier-lab",
            password="secret123",
            role="carrier",
        )
        carrier = carrier_user.carrier_profile
        order = Order.objects.create(client=client, carrier=carrier, priority=Order.Priority.URGENT, status=Order.Status.DELIVERED)

        self.client.login(username="lab-staff", password="secret123")
        response = self.client.get(reverse("accounts:role_redirect"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lab staff dashboard")
        self.assertContains(response, order.reference_code)

        confirm_response = self.client.post(reverse("tracking:order_mark_received", kwargs={"pk": order.pk}), follow=True)
        order.refresh_from_db()

        self.assertEqual(order.status, Order.Status.RECEIVED)
        self.assertContains(confirm_response, "marked received at lab")

    def test_dispatcher_can_assign_carrier_to_order(self):
        dispatcher = get_user_model().objects.create_user(
            username="dispatcher-flow",
            password="secret123",
            role="dispatcher",
        )
        client = Client.objects.create(name="Flow Clinic", contact_phone="0712345678", address="Nairobi")
        order = Order.objects.create(client=client, priority=Order.Priority.URGENT)
        carrier = Carrier.objects.create(phone="0755555555", status=Carrier.Status.AVAILABLE)

        self.client.login(username="dispatcher-flow", password="secret123")
        response = self.client.post(
            reverse("tracking:order_assign_carrier", kwargs={"pk": order.pk}),
            {"carrier": carrier.pk},
            follow=True,
        )

        order.refresh_from_db()
        carrier.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, Order.Status.ASSIGNED)
        self.assertEqual(order.carrier, carrier)
        self.assertEqual(carrier.status, Carrier.Status.ON_JOB)
        self.assertTrue(order.custody_events.filter(event_type="carrier_assigned").exists())

    def test_tracking_tables_reference_custom_user_model(self):
        carrier_fk = connection.cursor().execute("PRAGMA foreign_key_list(tracking_carrier)").fetchall()
        custody_fk = connection.cursor().execute("PRAGMA foreign_key_list(tracking_custodyevent)").fetchall()

        self.assertTrue(any(fk[2] == "accounts_user" for fk in carrier_fk))
        self.assertTrue(any(fk[2] == "accounts_user" for fk in custody_fk))

    def test_carrier_string_representation_handles_missing_user(self):
        carrier = Carrier(phone="0712345678")

        self.assertEqual(str(carrier), "Unnamed carrier")

    def test_notification_badge_and_mark_read(self):
        user = get_user_model().objects.create_user(
            username="ui-user",
            password="secret123",
            role="dispatcher",
        )

        # create two notifications, one will be marked read
        n1 = Notification.objects.create(user=user, message="First notification")
        n2 = Notification.objects.create(user=user, message="Second notification")

        self.client.login(username="ui-user", password="secret123")
        resp = self.client.get(reverse("tracking:dashboard"))
        self.assertEqual(resp.status_code, 200)
        # should show badge with 2 unread
        self.assertContains(resp, '<span class="badge">2</span>', html=True)
        self.assertContains(resp, "First notification")
        self.assertContains(resp, "Second notification")

        # mark the first notification as read via the view
        mark_url = reverse("tracking:notification_mark_read", kwargs={"pk": n1.pk}) + "?next=" + reverse("tracking:dashboard")
        resp2 = self.client.get(mark_url, follow=True)
        n1.refresh_from_db()
        self.assertTrue(n1.is_read)
        # badge should now show 1 unread
        self.assertContains(resp2, '<span class="badge">1</span>', html=True)

    def test_super_admin_and_dispatcher_can_view_carrier_monitoring(self):
        dispatcher = get_user_model().objects.create_user(
            username="dispatcher-monitor",
            password="secret123",
            role="dispatcher",
        )
        superuser = get_user_model().objects.create_superuser(
            username="admin-monitor",
            email="admin-monitor@example.com",
            password="secret123",
        )
        carrier_user = get_user_model().objects.create_user(
            username="carrier-live",
            password="secret123",
            role="carrier",
        )
        carrier = carrier_user.carrier_profile
        carrier.current_latitude = -1.2921
        carrier.current_longitude = 36.8219
        carrier.status = Carrier.Status.AVAILABLE
        carrier.save()

        for user in [dispatcher, superuser]:
            self.client.login(username=user.username, password="secret123")
            response = self.client.get(reverse("tracking:carrier_monitoring"))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Live carrier movement")
            self.assertContains(response, "Carrier monitoring")
            self.client.logout()

    def test_carrier_positions_endpoint_returns_json_positions(self):
        dispatcher = get_user_model().objects.create_user(
            username="dispatcher-positions",
            password="secret123",
            role="dispatcher",
        )
        carrier_user = get_user_model().objects.create_user(
            username="carrier-json",
            password="secret123",
            role="carrier",
        )
        carrier = carrier_user.carrier_profile
        carrier.current_latitude = -1.2921
        carrier.current_longitude = 36.8219
        carrier.status = Carrier.Status.AVAILABLE
        carrier.save()

        self.client.login(username="dispatcher-positions", password="secret123")
        response = self.client.get(reverse("tracking:carrier_positions"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"].split(";")[0], "application/json")
        data = response.json()
        self.assertIn("carriers", data)
        self.assertEqual(len(data["carriers"]), 1)
        self.assertEqual(data["carriers"][0]["name"], carrier_user.get_full_name() or carrier_user.username)




