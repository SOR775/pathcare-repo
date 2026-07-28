from django.shortcuts import render

from .models import SystemSetting


def core_index(request):
    settings = SystemSetting.objects.all()[:10]
    return render(request, "core/index.html", {"settings": settings})
