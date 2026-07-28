from django.conf import settings
from django.db import models


class CarrierAssignment(models.Model):
    """Represents a carrier's assigned operational capacity."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    carrier = models.OneToOneField(
        "tracking.Carrier",
        on_delete=models.CASCADE,
        related_name="module_assignment",
    )
    service_radius_km = models.PositiveIntegerField(default=50)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.carrier} ({self.service_radius_km}km)"
