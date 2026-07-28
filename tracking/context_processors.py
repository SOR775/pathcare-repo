from .models import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {}
    try:
        unread = Notification.objects.filter(user=request.user, is_read=False).count()
        recent = Notification.objects.filter(user=request.user).order_by("-created_at")[:10]
        return {"notifications_unread_count": unread, "notifications_list": recent}
    except Exception:
        return {}
