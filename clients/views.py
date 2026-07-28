from django.shortcuts import render

from tracking.models import Client


def client_index(request):
    clients = Client.objects.filter(is_active=True).order_by("name")
    return render(request, "clients/index.html", {"clients": clients, "profiles": clients})
