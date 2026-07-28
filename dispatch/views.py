from django.http import HttpResponse

from .models import DispatchRun


def dispatch_index(request):
    runs = DispatchRun.objects.all()[:10]
    lines = [run.run_name for run in runs]
    return HttpResponse("<br>".join(lines or ["No dispatch runs yet."]))
