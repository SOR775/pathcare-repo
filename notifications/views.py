from django.http import HttpResponse

from .models import NotificationLog


def notification_index(request):
    logs = NotificationLog.objects.select_related("recipient").all()[:10]
    lines = [f"{log.recipient.username}: {log.message}" for log in logs]
    return HttpResponse("<br>".join(lines or ["No notifications yet."]))
