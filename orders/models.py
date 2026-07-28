from django.db import models


class OrderWorkflow(models.Model):
    """A lightweight workflow record for order lifecycle tracking."""

    order = models.OneToOneField(
        "tracking.Order",
        on_delete=models.SET_NULL,
        related_name="workflow_state",
        null=True,
        blank=True,
    )
    handoff_window_minutes = models.PositiveIntegerField(default=30)
    requires_signature = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Workflow for {self.order.reference_code}"
