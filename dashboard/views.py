from django.http import HttpResponse

from .models import DashboardTile


def dashboard_index(request):
    tiles = DashboardTile.objects.all()[:10]
    lines = [f"{tile.title}: {tile.metric}" for tile in tiles]
    return HttpResponse("<br>".join(lines or ["No dashboard tiles yet."]))
