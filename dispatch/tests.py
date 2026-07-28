from django.test import TestCase

from .models import DispatchRun


class DispatchRunTests(TestCase):
    def test_dispatch_run_can_be_created(self):
        run = DispatchRun.objects.create(run_name="Morning Run")

        self.assertEqual(run.run_name, "Morning Run")
