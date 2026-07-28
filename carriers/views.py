from django.shortcuts import render

from .models import CarrierAssignment


def carrier_index(request):
    assignments = CarrierAssignment.objects.select_related("carrier").all()[:10]
    return render(request, "carriers/index.html", {"assignments": assignments})
