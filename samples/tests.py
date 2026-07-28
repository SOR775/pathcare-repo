from django.test import TestCase

from tracking.models import Order, Sample, Client
from .models import SampleCondition


class SampleConditionTests(TestCase):
    def test_sample_condition_can_be_created(self):
        client = Client.objects.create(
            name="Sample Receiver",
            contact_phone="555-0130",
            address="789 Test Road",
        )
        order = Order.objects.create(client=client, reference_code="ORD-2002")
        sample = Sample.objects.create(order=order, barcode="ABC-100", sample_type=Sample.SampleType.BLOOD)

        condition = SampleCondition.objects.create(sample=sample, temperature_celsius=4.5)

        self.assertEqual(condition.sample.barcode, "ABC-100")
        self.assertEqual(condition.temperature_celsius, 4.5)
