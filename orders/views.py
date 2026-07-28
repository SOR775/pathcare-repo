from django.shortcuts import render

from .models import OrderWorkflow


def order_index(request):
    workflows = OrderWorkflow.objects.select_related("order").all()[:10]
    return render(request, "orders/index.html", {"workflows": workflows})
