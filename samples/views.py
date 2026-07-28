from django.shortcuts import render

from .models import SampleCondition


def sample_index(request):
    conditions = SampleCondition.objects.select_related("sample").all()[:10]
    return render(request, "samples/index.html", {"conditions": conditions})
