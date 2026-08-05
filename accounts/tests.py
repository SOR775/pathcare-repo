from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from tracking.models import Client

from .models import AccountProfile, User


class LoginViewTests(TestCase):
    def test_login_creates_profile_for_carrier_user(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="carrier-login",
            password="secret",
            role=User.Role.CARRIER,
            phone="0712345678",
        )

        response = self.client.post(
            reverse("login"),
            {"username": "carrier-login", "password": "secret"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(AccountProfile.objects.filter(user=user).exists())
        self.assertEqual(user.account_profile.role, User.Role.CARRIER)


class AccountProfileTests(TestCase):
    def test_account_profile_is_created_for_user(self):
        user = get_user_model().objects.create_user(username="ops", password="secret")

        self.assertTrue(hasattr(user, "account_profile"))
        self.assertEqual(user.account_profile.role, User.Role.DISPATCHER)


class CustomUserTests(TestCase):
    def test_create_user_with_role(self):
        User = get_user_model()
        user = User.objects.create_user(username="dispatcher", password="secret", role=User.Role.DISPATCHER)

        self.assertEqual(user.role, User.Role.DISPATCHER)

    def test_role_redirect_sends_dispatcher_to_dashboard(self):
        User = get_user_model()
        user = User.objects.create_user(username="dispatch", password="secret", role=User.Role.DISPATCHER)

        self.client.force_login(user)
        response = self.client.get(reverse("accounts:role_redirect"))

        self.assertRedirects(response, reverse("tracking:dashboard"))

    def test_role_redirect_sends_lab_staff_to_lab_dashboard(self):
        User = get_user_model()
        user = User.objects.create_user(username="labworker", password="secret", role=User.Role.LAB_STAFF)

        self.client.force_login(user)
        response = self.client.get(reverse("accounts:role_redirect"))

        self.assertRedirects(response, reverse("tracking:lab_dashboard"))

    def test_superuser_is_treated_as_super_admin(self):
        User = get_user_model()
        user = User.objects.create_superuser(username="superuser", email="superuser@example.com", password="secret")

        self.assertTrue(user.is_super_admin())
        self.assertEqual(user.role, User.Role.SUPER_ADMIN)
        self.assertFalse(user.is_dispatcher())
        self.assertFalse(user.is_carrier())
        self.assertFalse(user.is_client())
        self.assertFalse(user.is_lab_staff())

    def test_seed_users_creates_super_admin_account(self):
        out = StringIO()
        call_command("seed_users", stdout=out)

        super_admin = get_user_model().objects.filter(username="pkl-super.admin").first()
        self.assertIsNotNone(super_admin)
        self.assertTrue(super_admin.is_super_admin())
        self.assertEqual(super_admin.role, User.Role.SUPER_ADMIN)

    def test_super_admin_can_create_user_with_template_password_fields(self):
        super_admin = get_user_model().objects.create_superuser(
            username="admin-creator",
            email="admin-creator@example.com",
            password="secret",
        )
        self.client.force_login(super_admin)

        response = self.client.post(
            reverse("accounts:user_management"),
            {
                "first_name": "Jane",
                "last_name": "Doe",
                "username": "jane-doe",
                "email": "jane@example.com",
                "phone": "0712345678",
                "role": User.Role.DISPATCHER,
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user_model().objects.filter(username="jane-doe").exists())

    def test_creating_carrier_user_creates_carrier_profile(self):
        User = get_user_model()
        user = User.objects.create_user(username="driver", password="secret", role=User.Role.CARRIER, phone="0712345678")

        self.assertTrue(hasattr(user, "carrier_profile"))
        self.assertEqual(user.carrier_profile.phone, "0712345678")

    def test_creating_client_user_creates_tracking_client(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="client-user",
            password="secret",
            role=User.Role.CLIENT,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone="0712345678",
        )

        client = Client.objects.filter(contact_email="jane@example.com").first()
        self.assertIsNotNone(client)
        self.assertEqual(client.name, "Jane Doe")
        self.assertEqual(client.contact_phone, "0712345678")
