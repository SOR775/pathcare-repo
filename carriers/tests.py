from django.contrib.auth import get_user_model
from django.test import TestCase

from tracking.models import Carrier
from .models import CarrierAssignment


class CarrierAssignmentTests(TestCase):
    def test_carrier_assignment_can_be_created(self):
        user = get_user_model().objects.create_user(username="driver", password="secret")
        carrier = Carrier.objects.create(user=user, phone="555-0101")

        assignment = CarrierAssignment.objects.create(carrier=carrier, service_radius_km=80)

        self.assertEqual(assignment.carrier.user.username, "driver")
        self.assertEqual(assignment.service_radius_km, 80)
