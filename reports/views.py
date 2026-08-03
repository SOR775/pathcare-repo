import csv
import json
from collections import Counter
from datetime import timedelta

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from tracking.models import Order

from .models import ReportSnapshot


def _chart_series(orders_qs, value_getter, limit=8):
    counts = Counter(value_getter(order) for order in orders_qs if value_getter(order))
    items = counts.most_common(limit)
    return {
        "labels": [label for label, _ in items],
        "data": [count for _, count in items],
    }


def _daily_pickups_series(orders_qs, days=7):
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days - 1)
    labels = []
    data = []
    for offset in range(days):
        current_day = start_date + timedelta(days=offset)
        labels.append(current_day.strftime("%b %d"))
        data.append(orders_qs.filter(created_at__date=current_day).count())
    return {"labels": labels, "data": data}


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

    status_counts = Counter(order.get_status_display() for order in orders_qs)
    chart_data = {
        "status": dict(status_counts),
        "pickups_per_day": _daily_pickups_series(orders_qs),
        "samples_by_laboratory": _chart_series(
            orders_qs,
            lambda order: order.facility.name if order.facility else "Unassigned",
        ),
        "carrier_performance": _chart_series(
            orders_qs,
            lambda order: order.carrier.display_name if order.carrier else "Unassigned",
        ),
        "orders_by_client": _chart_series(
            orders_qs,
            lambda order: order.client.name if order.client else "Unassigned",
        ),
    }

    completed_orders = orders_qs.filter(
        status__in=[Order.Status.DELIVERED, Order.Status.RECEIVED, Order.Status.COMPLETED]
    ).exclude(updated_at__isnull=True)
    delivery_hours = []
    for order in completed_orders:
        if order.created_at and order.updated_at:
            delivery_hours.append((order.updated_at - order.created_at).total_seconds() / 3600)

    delay_regions = Counter()
    for order in orders_qs:
        if order.client and order.client.address:
            region = order.client.address.split(",")[-1].strip() or "Unknown"
            delay_regions[region] += 1
        else:
            delay_regions["Unknown"] += 1

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
            "status_counts_json": json.dumps(dict(status_counts)),
            "chart_data_json": json.dumps(chart_data),
            "delivery_time_avg_hours": round(sum(delivery_hours) / len(delivery_hours), 1) if delivery_hours else 0,
            "delivery_time_completed_orders": completed_orders.count(),
            "delay_regions": delay_regions.most_common(5),
        },
    )
