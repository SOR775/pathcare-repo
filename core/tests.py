from django.test import TestCase
from django.urls import reverse

from .models import SystemSetting


class SystemSettingTests(TestCase):
    def test_system_setting_can_be_created(self):
        setting = SystemSetting.objects.create(key="site_name", value="PathCare")

        self.assertEqual(setting.key, "site_name")
        self.assertEqual(setting.value, "PathCare")


class CoreIndexViewTests(TestCase):
    def test_core_index_page_lists_operational_modules(self):
        SystemSetting.objects.create(key="site_name", value="PathCare")

        response = self.client.get(reverse("core:core_index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operations modules")
        self.assertContains(response, "site_name")
        self.assertContains(response, "Accounts")
        self.assertContains(response, reverse("accounts:account_index"))
