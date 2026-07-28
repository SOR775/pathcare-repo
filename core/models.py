from django.db import models
import uuid


class Facility(models.Model):
    """A facility (hospital, clinic, warehouse) where clients request pickups."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True, help_text="Facility latitude for routing")
    longitude = models.FloatField(null=True, blank=True, help_text="Facility longitude for routing")
    contact_name = models.CharField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    contact_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class SystemSetting(models.Model):
    """A simple application setting container."""

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.key
