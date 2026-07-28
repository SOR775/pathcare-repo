from django.test import TestCase

from tracking.models import Client
from .models import ClientProfile


class ClientProfileTests(TestCase):
    def test_client_profile_can_be_created(self):
        client = Client.objects.create(
            name="Sample Lab",
            contact_phone="555-0100",
            address="123 Test Street",
        )

        profile = ClientProfile.objects.create(client=client, service_level="priority")

        self.assertEqual(profile.client.name, "Sample Lab")
        self.assertEqual(profile.service_level, "priority")
