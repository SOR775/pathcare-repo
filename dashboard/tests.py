from django.test import TestCase

from .models import DashboardTile


class DashboardTileTests(TestCase):
    def test_dashboard_tile_can_be_created(self):
        tile = DashboardTile.objects.create(title="Orders", metric="12")

        self.assertEqual(tile.title, "Orders")
        self.assertEqual(tile.metric, "12")
