import csv

from django.http import HttpResponse
from django.shortcuts import render

from tracking.models import Order

from .models import ReportSnapshot


def report_index(request):
    status_filter = request.GET.get("status", "")
    download = request.GET.get("download", "")

    orders_qs = Order.objects.select_related("client", "carrier")
    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)

    orders = orders_qs.order_by("-created_at")[:20]
    snapshots = ReportSnapshot.objects.all().order_by("-created_at")[:10]

    summary = {
        "total_orders": Order.objects.count(),
        "pending": Order.objects.filter(status=Order.Status.PENDING).count(),
        "delivered": Order.objects.filter(status=Order.Status.DELIVERED).count(),
        "urgent": Order.objects.filter(priority=Order.Priority.STAT).count(),
        "exceptions": Order.objects.filter(status=Order.Status.CANCELLED).count(),
    }

    if download == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=pathcare_orders_report.csv"
        writer = csv.writer(response)
        writer.writerow(["reference_code", "client", "carrier", "status", "created_at"])
        for order in orders_qs.order_by("-created_at"):
            writer.writerow([
                order.reference_code,
                order.client.name,
                order.carrier.display_name if order.carrier else "Unassigned",
                order.get_status_display(),
                order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])
        return response

    return render(
        request,
        "reports/report_index.html",
        {
            "snapshots": snapshots,
            "orders": orders,
            "summary": summary,
            "status_filter": status_filter,
            "statuses": Order.Status.choices,
        },
    )
