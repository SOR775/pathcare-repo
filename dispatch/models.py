from django.db import models


class DispatchRun(models.Model):
    """A dispatch run grouping one or more orders."""

    run_name = models.CharField(max_length=100)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.run_name
