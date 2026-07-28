from django.shortcuts import render

from .models import CustodyCheckpoint


def custody_index(request):
    checkpoints = CustodyCheckpoint.objects.select_related("order").all()[:10]
    return render(request, "custody/index.html", {"checkpoints": checkpoints})
