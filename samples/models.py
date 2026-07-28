from django.db import models


class SampleCondition(models.Model):
    """Operational condition details recorded for a sample."""

    sample = models.OneToOneField(
        "tracking.Sample",
        on_delete=models.SET_NULL,
        related_name="condition_record",
        null=True,
        blank=True,
    )
    temperature_celsius = models.FloatField(default=0.0)
    is_sealed = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Condition for {self.sample.barcode}"
