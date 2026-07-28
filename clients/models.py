from django.db import models


class ClientProfile(models.Model):
    """Operational profile attached to a client record."""

    client = models.OneToOneField(
        "tracking.Client",
        on_delete=models.CASCADE,
        related_name="module_profile",
    )
    service_level = models.CharField(max_length=32, default="standard")
    onboarding_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client.name} ({self.service_level})"
