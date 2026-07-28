from django.db import models


class ReportSnapshot(models.Model):
    """Saved report snapshot for operational review."""

    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
