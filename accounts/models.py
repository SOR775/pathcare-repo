from django.apps import apps
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class PathcareUserManager(UserManager):
    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.SUPER_ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model for Pathcare with role-based access."""

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        DISPATCHER = "dispatcher", "Dispatcher"
        CARRIER = "carrier", "Carrier"
        CLIENT = "client", "Client"
        LAB_STAFF = "lab_staff", "Lab Staff"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DISPATCHER)
    phone = models.CharField(max_length=32, blank=True)
    department = models.CharField(max_length=100, blank=True)

    objects = PathcareUserManager()

    def is_super_admin(self):
        return self.is_superuser or self.role == self.Role.SUPER_ADMIN

    def is_dispatcher(self):
        return not self.is_superuser and self.role == self.Role.DISPATCHER

    def is_carrier(self):
        return not self.is_superuser and self.role == self.Role.CARRIER

    def is_client(self):
        return not self.is_superuser and self.role == self.Role.CLIENT

    def is_lab_staff(self):
        return not self.is_superuser and self.role == self.Role.LAB_STAFF

    def __str__(self):
        return self.get_full_name() or self.username

    def ensure_profiles(self):
        profile = None
        try:
            profile = AccountProfile.objects.get(user=self)
        except AccountProfile.DoesNotExist:
            profile = AccountProfile.objects.create(
                user=self,
                role=self.role,
                phone=self.phone,
                department=self.department,
            )

        if profile.role != self.role or profile.phone != self.phone or profile.department != self.department:
            profile.role = self.role
            profile.phone = self.phone
            profile.department = self.department
            profile.save()

        if self.role == User.Role.CARRIER:
            Carrier = apps.get_model("tracking", "Carrier")
            if not Carrier.objects.filter(user=self).exists():
                Carrier.objects.create(user=self, phone=self.phone or "")

        if self.role == User.Role.CLIENT:
            Client = apps.get_model("tracking", "Client")
            client_name = self.get_full_name() or self.username
            client, created = Client.objects.get_or_create(
                contact_email=self.email,
                defaults={
                    "name": client_name,
                    "contact_name": self.get_full_name() or self.username,
                    "contact_phone": self.phone,
                    "address": "",
                },
            )
            if not client.name:
                client.name = client_name
            if not client.contact_name:
                client.contact_name = self.get_full_name() or self.username
            if not client.contact_phone and self.phone:
                client.contact_phone = self.phone
            if not client.contact_email and self.email:
                client.contact_email = self.email
            client.save()


@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    update_fields = kwargs.get("update_fields")
    if update_fields == {"last_login"}:
        return
    instance.ensure_profiles()


class AccountProfile(models.Model):
    """Operational profile for a user who can access the logistics workspace."""

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="account_profile",
    )
    role = models.CharField(max_length=20, choices=User.Role.choices, default=User.Role.DISPATCHER)
    phone = models.CharField(max_length=32, blank=True)
    department = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role})"
