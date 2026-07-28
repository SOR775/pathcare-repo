from django.db import models


class CustodyCheckpoint(models.Model):
    """A lightweight append-only checkpoint for custody events."""

    order = models.ForeignKey(
        "tracking.Order",
        on_delete=models.SET_NULL,
        related_name="custody_checkpoints",
        null=True,
        blank=True,
    )
    checkpoint_name = models.CharField(max_length=100)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.checkpoint_name} for {self.order.reference_code}"
