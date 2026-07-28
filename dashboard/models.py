from django.db import models


class DashboardTile(models.Model):
    """A simple dashboard tile descriptor for the operations view."""

    title = models.CharField(max_length=100)
    metric = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
