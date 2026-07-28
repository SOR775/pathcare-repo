import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.forms import formset_factory
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect

from accounts.decorators import role_required
from core.models import Facility
from .forms import (
    AssignCarrierForm,
    CarrierForm,
    CarrierIssueForm,
    CarrierIssueReplyForm,
    ClientForm,
    ClientPickupRequestForm,
    FacilityForm,
    OrderForm,
    SampleForm,
)
from .models import Carrier, CarrierIssue, CarrierIssueReply, Client, CustodyEvent, Order, Sample, Notification

User = get_user_model()


def _user_role(user):
    if not user.is_authenticated:
        return None
    if getattr(user, "is_super_admin", lambda: False)():
        return "Super Admin"
    if hasattr(user, "carrier_profile"):
        return "Carrier"
    if hasattr(user, "get_role_display"):
        return user.get_role_display()
    return "Dispatcher"


def _haversine_distance(lat1, lon1, lat2, lon2):
    import math

    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def _estimate_minutes(distance_km, speed_kmh=40):
    if distance_km is None:
        return None
    return int(round(distance_km / speed_kmh * 60))


def _suggest_carriers_for_order(order, limit=5):
    available_carriers = (
        Carrier.objects.filter(is_active=True, status=Carrier.Status.AVAILABLE)
        .exclude(orders__status__in=Order.active_statuses())
        .select_related("user")
    )
    carriers = []
    for carrier in available_carriers:
        distance_km = None
        if order.latitude is not None and order.longitude is not None and carrier.current_latitude is not None and carrier.current_longitude is not None:
            distance_km = _haversine_distance(order.latitude, order.longitude, carrier.current_latitude, carrier.current_longitude)
        carriers.append({
            "carrier": carrier,
            "distance_km": distance_km,
        })
    carriers.sort(key=lambda item: (item["distance_km"] is None, item["distance_km"] if item["distance_km"] is not None else 999999, item["carrier"].display_name.lower()))
    return carriers[:limit]


def _order_queryset_for_user(user):
    if not user.is_authenticated:
        return Order.objects.none()
    if getattr(user, "is_super_admin", lambda: False)() or user.is_dispatcher():
        return Order.objects.all()
    if user.is_carrier():
        carrier = getattr(user, "carrier_profile", None)
        if carrier is None:
            return Order.objects.none()
        return Order.objects.filter(carrier=carrier)
    if user.is_client():
        return Order.objects.filter(client__contact_email=user.email)
    if user.is_lab_staff():
        return Order.objects.filter(status__in=[Order.Status.DELIVERED, Order.Status.RECEIVED, Order.Status.COMPLETED])
    return Order.objects.none()


def _get_order_for_user(user, pk):
    return get_object_or_404(_order_queryset_for_user(user).select_related("client", "carrier"), pk=pk)


@role_required("super_admin", "dispatcher", "carrier", "client", "lab_staff")
def dashboard(request):
    role = _user_role(request.user)
    now = timezone.localtime()

    orders = _order_queryset_for_user(request.user).select_related("client", "carrier").order_by("-created_at")

    dispatcher_context = {}
    carrier_context = {}
    client_context = {}
    user_counts = {}
    clients = Client.objects.all().order_by("name")
    user_client = None
    try:
        user_client = Client.objects.filter(contact_email=getattr(request.user, "email", None)).first()
    except Exception:
        user_client = None

    if role == "Super Admin":
        dispatcher_context.update({
            "recent_activity": CustodyEvent.objects.order_by("-timestamp")[:10],
            "recent_orders": Order.objects.order_by("-created_at")[:5],
            "recent_carriers": Carrier.objects.filter(is_active=True)[:10],
            "available_carriers": Carrier.objects.filter(status=Carrier.Status.AVAILABLE, is_active=True).count(),
            "busy_carriers": Carrier.objects.filter(status=Carrier.Status.ON_JOB, is_active=True).count(),
            "offline_carriers": Carrier.objects.filter(status=Carrier.Status.OFFLINE, is_active=True).count(),
            "custody_events": CustodyEvent.objects.order_by("-timestamp")[:15],
            "facilities": Facility.objects.filter(is_active=True).order_by("name"),
        })
        # Add user_counts for Super Admin dashboard stats
        user_counts = {
            "total_users": User.objects.filter(is_active=True).count(),
            "active_orders": Order.objects.filter(status__in=[Order.Status.PENDING_REVIEW, Order.Status.PENDING, Order.Status.ASSIGNED, Order.Status.ACCEPTED, Order.Status.EN_ROUTE_TO_CLIENT, Order.Status.AT_CLIENT, Order.Status.PICKED_UP, Order.Status.IN_TRANSIT]).count(),
            "completed_deliveries": Order.objects.filter(status__in=[Order.Status.DELIVERED, Order.Status.RECEIVED, Order.Status.COMPLETED]).count(),
            "pending_pickups": Order.objects.filter(status=Order.Status.PENDING).count(),
            "samples_in_transit": Sample.objects.filter(order__status__in=[Order.Status.IN_TRANSIT, Order.Status.EN_ROUTE_TO_CLIENT, Order.Status.AT_CLIENT, Order.Status.PICKED_UP]).count(),
            "delayed_deliveries": Order.objects.filter(status__in=[Order.Status.PENDING_REVIEW, Order.Status.PENDING, Order.Status.ASSIGNED, Order.Status.ACCEPTED]).count(),
            "active_carriers": Carrier.objects.filter(is_active=True).count(),
            "registered_clients": Client.objects.filter(is_active=True).count(),
            "total_facilities": Facility.objects.filter(is_active=True).count(),
        }

    if role == "Dispatcher":
        today = now.date()
        dispatcher_context = {
            "pickup_requests_today": Order.objects.filter(requested_pickup_time__date=today).count(),
            "orders_pending_review": Order.objects.filter(status=Order.Status.PENDING_REVIEW).count(),
            "orders_awaiting_assignment": Order.objects.filter(status=Order.Status.PENDING).count(),
            "available_carriers": Carrier.objects.filter(status=Carrier.Status.AVAILABLE, is_active=True).count(),
            "busy_carriers": Carrier.objects.filter(status=Carrier.Status.ON_JOB, is_active=True).count(),
            "offline_carriers": Carrier.objects.filter(status=Carrier.Status.OFFLINE, is_active=True).count(),
            "delayed_orders": Order.objects.filter(status__in=[Order.Status.PENDING_REVIEW, Order.Status.PENDING, Order.Status.ASSIGNED]).exclude(requested_pickup_time__isnull=True).filter(requested_pickup_time__lt=now).count(),
            "completed_today": Order.objects.filter(status__in=[Order.Status.DELIVERED, Order.Status.RECEIVED, Order.Status.COMPLETED], updated_at__date=today).count(),
            "dispatch_queue": orders.filter(status__in=[Order.Status.PENDING_REVIEW, Order.Status.PENDING, Order.Status.ASSIGNED])[:10],
            "today_schedule": Order.objects.filter(
                Q(requested_pickup_time__date=today) | Q(status__in=[Order.Status.PENDING_REVIEW, Order.Status.PENDING, Order.Status.ASSIGNED])
            ).order_by("requested_pickup_time")[:10],
            "recent_carriers": Carrier.objects.filter(is_active=True)[:10],
            "recent_activity": CustodyEvent.objects.order_by("-timestamp")[:10],
            "custody_events": CustodyEvent.objects.filter(order__in=orders).order_by("-timestamp")[:20],
            "facilities": Facility.objects.filter(is_active=True).order_by("name")[:15],
        }

    if role == "Carrier":
        carrier = getattr(request.user, "carrier_profile", None)
        assigned_orders = Order.objects.filter(carrier=carrier).select_related("client").order_by("-created_at")
        carrier_context = {
            "carrier": carrier,
            "assigned_orders": assigned_orders,
            "completed_today": Order.objects.filter(carrier=carrier, status__in=[Order.Status.DELIVERED, Order.Status.RECEIVED, Order.Status.COMPLETED], updated_at__date=now.date()).count(),
            "pending_pickups": Order.objects.filter(carrier=carrier, status__in=[Order.Status.ASSIGNED, Order.Status.ACCEPTED, Order.Status.EN_ROUTE_TO_CLIENT, Order.Status.AT_CLIENT]).count(),
            "pending_deliveries": Order.objects.filter(carrier=carrier, status__in=[Order.Status.PICKED_UP, Order.Status.IN_TRANSIT]).count(),
            "custody_events": CustodyEvent.objects.filter(order__carrier=carrier).order_by("-timestamp")[:15],
        }

    if role == "Client":
        client_obj = None
        try:
            client_obj = Client.objects.filter(contact_email=request.user.email).first()
        except Exception:
            client_obj = None
        if client_obj:
            client_context = {
                "client": client_obj,
                "recent_orders": Order.objects.filter(client=client_obj).order_by("-created_at")[:10],
                "pickup_requests": Order.objects.filter(client=client_obj, status=Order.Status.PENDING_REVIEW).count(),
                "active_orders": Order.objects.filter(client=client_obj, status__in=[Order.Status.PENDING, Order.Status.ASSIGNED, Order.Status.ACCEPTED, Order.Status.EN_ROUTE_TO_CLIENT, Order.Status.AT_CLIENT, Order.Status.PICKED_UP, Order.Status.IN_TRANSIT]).count(),
                "delivered_samples": Sample.objects.filter(order__client=client_obj, is_received=True).count(),
                "custody_events": CustodyEvent.objects.filter(order__client=client_obj).order_by("-timestamp")[:15],
            }

    # Handle order filtering for the orders table
    status_filter = request.GET.get("status", "")
    if status_filter:
        orders_table = orders.filter(status=status_filter)
    else:
        orders_table = orders
    
    # Prepare counts based on the visible order set for this user
    counts = {
        "pending": orders.filter(status=Order.Status.PENDING).count(),
        "assigned": orders.filter(status=Order.Status.ASSIGNED).count(),
        "in_transit": orders.filter(status=Order.Status.IN_TRANSIT).count(),
        "delivered": orders.filter(status__in=[Order.Status.DELIVERED, Order.Status.RECEIVED, Order.Status.COMPLETED]).count(),
    }
    
    # Add orders_in_transit to dispatcher context if not already there
    if role == "Dispatcher" and "orders_in_transit" not in dispatcher_context:
        dispatcher_context["orders_in_transit"] = Order.objects.filter(status=Order.Status.IN_TRANSIT).count()

    context = {
        "role": role,
        "dispatcher_context": dispatcher_context,
        "carrier_context": carrier_context,
        "client_context": client_context,
        "user_counts": user_counts,
        "clients": clients,
        "user_client": user_client,
        "lab_location": settings.LAB_LOCATION,
        "orders": orders_table,
        "statuses": Order.Status.choices,
        "status_filter": status_filter,
        "counts": counts,
    }
    
    return render(request, "tracking/dashboard.html", context)


@role_required("super_admin", "dispatcher")
def client_list(request):
    clients = Client.objects.filter(is_active=True).order_by("name")
    page = request.GET.get("page", 1)
    paginator = Paginator(clients, 15)
    clients = paginator.get_page(page)

    query_params = request.GET.copy()
    if "page" in query_params:
        del query_params["page"]

    return render(request, "tracking/client_list.html", {
        "clients": clients,
        "form": ClientForm(),
        "page_obj": clients,
        "querystring": query_params.urlencode(),
    })


@role_required("super_admin", "dispatcher")
def client_create(request):
    clients = Client.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Client added.")
            return redirect("tracking:client_list")

        messages.error(request, "Please complete the required client details before saving.")
        return render(request, "tracking/client_list.html", {"clients": clients, "form": form})

    return render(request, "tracking/client_list.html", {"clients": clients, "form": ClientForm()})


@role_required("super_admin", "dispatcher", "client")
def client_request_pickup(request):
    SampleRequestFormSet = formset_factory(SampleForm, extra=1, min_num=1, validate_min=True)

    # Get the client associated with this user (matched by email)
    user_client = None
    try:
        user_client = Client.objects.filter(contact_email=request.user.email).first()
    except Exception:
        user_client = None

    if request.method == "POST":
        form = ClientPickupRequestForm(request.POST)
        sample_formset = SampleRequestFormSet(request.POST, prefix="samples")
        if form.is_valid() and sample_formset.is_valid():
            facility_obj = form.cleaned_data["facility"]
            client_obj = user_client  # Use the authenticated user's client

            if not client_obj:
                messages.error(request, "No client profile associated with your account. Please contact support.")
                return redirect("tracking:dashboard")

            order = Order.objects.create(
                client=client_obj,
                facility=facility_obj,
                priority=form.cleaned_data["priority"],
                requested_pickup_time=form.cleaned_data["requested_pickup_time"],
                samples_ready_at=form.cleaned_data.get("samples_ready_at"),
                requestor_name=form.cleaned_data.get("contact_person", ""),
                requestor_phone=form.cleaned_data.get("contact_phone", ""),
                reception_details=form.cleaned_data.get("reception_details", ""),
                parking_notes=form.cleaned_data.get("parking_notes", ""),
                security_instructions=form.cleaned_data.get("security_instructions", ""),
                pickup_address=form.cleaned_data.get("pickup_address", ""),
                latitude=form.cleaned_data.get("latitude") or facility_obj.latitude,
                longitude=form.cleaned_data.get("longitude") or facility_obj.longitude,
                notes=form.cleaned_data.get("notes", ""),
                status=Order.Status.PENDING_REVIEW,
            )
            if order.latitude is not None and order.longitude is not None:
                lab = settings.LAB_LOCATION
                order.distance_to_lab_km = _haversine_distance(order.latitude, order.longitude, lab["latitude"], lab["longitude"])
                order.estimated_pickup_minutes = _estimate_minutes(order.distance_to_lab_km)
            order.save()

            for sample_form in sample_formset.cleaned_data:
                if not sample_form:
                    continue
                Sample.objects.create(
                    order=order,
                    barcode=sample_form.get("barcode") or f"{order.reference_code}-{order.samples.count()+1}",
                    sample_type=sample_form.get("sample_type"),
                    cold_chain_requirement=sample_form.get("cold_chain_requirement"),
                )

            CustodyEvent.objects.create(
                order=order,
                event_type=CustodyEvent.EventType.ORDER_CREATED,
                actor=request.user,
                notes="Pickup request submitted by client.",
                latitude=order.latitude,
                longitude=order.longitude,
            )
            # notify dispatcher users
            from django.contrib.auth import get_user_model
            User = get_user_model()
            for dispatcher in User.objects.filter(role=User.Role.DISPATCHER, is_active=True):
                try:
                    Notification.objects.create(
                        user=dispatcher,
                        order=order,
                        message=f"New pickup request {order.reference_code} requires review.",
                    )
                except Exception:
                    pass
            messages.success(request, "Pickup request submitted successfully.")
            return redirect("tracking:dashboard")
        # Support legacy simple POST payloads used by earlier clients/tests
        if "pickup_location" in request.POST:
            pickup_location = request.POST.get("pickup_location")
            contact_person = request.POST.get("contact_person") or pickup_location
            contact_phone = request.POST.get("contact_phone")
            priority = request.POST.get("priority") or Order.Priority.ROUTINE
            temp_req = request.POST.get("temperature_requirement")
            notes = request.POST.get("notes", "")
            sample_type = request.POST.get("sample_type")
            sample_count = int(request.POST.get("sample_count") or 1)

            client_obj = Client.objects.create(name=contact_person, contact_phone=contact_phone, address=pickup_location)
            order = Order.objects.create(client=client_obj, priority=priority, notes=notes, status=Order.Status.PENDING)
            for i in range(sample_count):
                Sample.objects.create(order=order, barcode=f"{order.reference_code}-{i+1}", sample_type=sample_type)
            CustodyEvent.objects.create(order=order, event_type=CustodyEvent.EventType.ORDER_CREATED, actor=request.user)
            messages.success(request, "Pickup request submitted successfully.")
            return redirect("tracking:dashboard")

        messages.error(request, "Please complete the pickup request form correctly.")
    else:
        form = ClientPickupRequestForm()
        sample_formset = SampleRequestFormSet(prefix="samples")

    return render(request, "tracking/client_pickup_request.html", {"form": form, "sample_formset": sample_formset, "lab_location": settings.LAB_LOCATION})


@role_required("super_admin", "dispatcher", "carrier")
def update_carrier_location(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=405)
    carrier_profile = getattr(request.user, "carrier_profile", None)
    if not carrier_profile:
        return JsonResponse({"error": "Carrier profile not found."}, status=403)

    try:
        if request.content_type == "application/json":
            payload = json.loads(request.body.decode("utf-8") or "{}")
        else:
            payload = request.POST
        latitude = float(payload.get("latitude"))
        longitude = float(payload.get("longitude"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid latitude/longitude values."}, status=400)

    carrier_profile.current_latitude = latitude
    carrier_profile.current_longitude = longitude
    carrier_profile.last_location_update = timezone.localtime()
    carrier_profile.save()
    return JsonResponse({
        "status": "ok",
        "latitude": latitude,
        "longitude": longitude,
        "updated_at": carrier_profile.last_location_update.isoformat(),
    })


@role_required("super_admin", "dispatcher")
def order_approve_request(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST" and order.status == Order.Status.PENDING_REVIEW:
        order.status = Order.Status.PENDING
        order.save()
        CustodyEvent.objects.create(
            order=order,
            event_type=CustodyEvent.EventType.REQUEST_APPROVED,
            actor=request.user,
            notes="Pickup request approved by dispatcher.",
        )
        try:
            if order.client and order.client.contact_email:
                User = get_user_model()
                client_user = User.objects.filter(email=order.client.contact_email).first()
                if client_user:
                    Notification.objects.create(
                        user=client_user,
                        order=order,
                        message=f"Your pickup request {order.reference_code} has been approved and is awaiting carrier assignment.",
                    )
        except Exception:
            pass
        messages.success(request, "Pickup request approved.")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "dispatcher")
def carrier_list(request):
    carriers = Carrier.objects.filter(is_active=True).select_related("user").order_by("user__first_name")
    page = request.GET.get("page", 1)
    paginator = Paginator(carriers, 15)
    carriers = paginator.get_page(page)

    query_params = request.GET.copy()
    if "page" in query_params:
        del query_params["page"]

    return render(request, "tracking/carrier_list.html", {
        "carriers": carriers,
        "form": CarrierForm(),
        "page_obj": carriers,
        "querystring": query_params.urlencode(),
    })


@role_required("super_admin", "dispatcher")
def carrier_create(request):
    if request.method == "POST":
        form = CarrierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Carrier added.")
            return redirect("tracking:carrier_list")
    else:
        form = CarrierForm()
    return render(request, "tracking/carrier_list.html", {"carriers": Carrier.objects.filter(is_active=True), "form": form})


@role_required("super_admin", "carrier")
def carrier_view(request):
    carrier = getattr(request.user, "carrier_profile", None)
    orders = Order.objects.filter(carrier=carrier).order_by("-created_at")
    next_pickup_order = Order.objects.filter(
        carrier=carrier,
        status__in=[
            Order.Status.ASSIGNED,
            Order.Status.ACCEPTED,
            Order.Status.EN_ROUTE_TO_CLIENT,
            Order.Status.AT_CLIENT,
        ],
        latitude__isnull=False,
        longitude__isnull=False,
    ).order_by("requested_pickup_time").first()

    lab_return_order = Order.objects.filter(
        carrier=carrier,
        status__in=[
            Order.Status.PICKED_UP,
            Order.Status.IN_TRANSIT,
            Order.Status.DELIVERED,
        ],
    ).order_by("requested_pickup_time").first()

    issue_form = None
    if request.method == "POST" and "issue_submit" in request.POST:
        issue_form = CarrierIssueForm(request.POST)
        if issue_form.is_valid():
            issue = issue_form.save(commit=False)
            issue.carrier = carrier
            if not issue.order and next_pickup_order:
                issue.order = next_pickup_order
            issue.save()
            review_users = User.objects.filter(role__in=[User.Role.SUPER_ADMIN, User.Role.DISPATCHER], is_active=True)
            for recipient in review_users:
                Notification.objects.create(
                    user=recipient,
                    order=issue.order,
                    message=f"Carrier {carrier.display_name} reported {issue.get_category_display()}: {issue.description[:120]}",
                )
            messages.success(request, "Issue reported. Dispatcher and admin have been notified.")
            return redirect("tracking:carrier_view")
    else:
        issue_form = CarrierIssueForm(initial={
            "order": next_pickup_order.pk if next_pickup_order else None,
        })

    orders = orders.prefetch_related('samples')
    carrier_location = None
    next_pickup_distance_km = None
    next_pickup_eta_minutes = None
    lab_location = {
        "latitude": settings.LAB_LOCATION["latitude"],
        "longitude": settings.LAB_LOCATION["longitude"],
    }
    if carrier and carrier.current_latitude is not None and carrier.current_longitude is not None:
        carrier_location = {
            "latitude": carrier.current_latitude,
            "longitude": carrier.current_longitude,
        }

    active_destination = None
    if lab_return_order:
        active_destination = lab_location
    elif next_pickup_order:
        active_destination = {
            "latitude": next_pickup_order.latitude,
            "longitude": next_pickup_order.longitude,
        }

    if active_destination and carrier_location:
        next_pickup_distance_km = _haversine_distance(
            carrier.current_latitude,
            carrier.current_longitude,
            active_destination["latitude"],
            active_destination["longitude"],
        )
        next_pickup_eta_minutes = _estimate_minutes(next_pickup_distance_km, speed_kmh=35)

    total_pickups = orders.count()
    total_samples = sum(order.samples.count() for order in orders)
    completed_pickups = orders.filter(status__in=[
        Order.Status.DELIVERED,
        Order.Status.RECEIVED,
        Order.Status.COMPLETED,
    ]).count()
    gps_active = carrier_location is not None
    connected = carrier.user.is_active if carrier and carrier.user else False
    carrier_issues = CarrierIssue.objects.filter(carrier=carrier).order_by("-created_at")[:8]

    return render(request, "tracking/carrier_view.html", {
        "carrier": carrier,
        "orders": orders,
        "next_pickup_order": next_pickup_order,
        "lab_return_order": lab_return_order,
        "carrier_location": carrier_location,
        "lab_location": lab_location,
        "next_pickup_distance_km": next_pickup_distance_km,
        "next_pickup_eta_minutes": next_pickup_eta_minutes,
        "total_pickups": total_pickups,
        "total_samples": total_samples,
        "completed_pickups": completed_pickups,
        "gps_active": gps_active,
        "connected": connected,
        "issue_form": issue_form,
        "carrier_issues": carrier_issues,
    })


@role_required("super_admin", "dispatcher", "carrier")
def carrier_issue_list(request):
    if request.user.is_carrier():
        carrier = getattr(request.user, "carrier_profile", None)
        issues = CarrierIssue.objects.filter(carrier=carrier)
    else:
        issues = CarrierIssue.objects.all()

    issues = issues.select_related("carrier__user", "order").order_by("-created_at")

    return render(request, "tracking/carrier_issue_list.html", {
        "issues": issues,
    })


@role_required("super_admin", "dispatcher", "carrier")
def carrier_issue_detail(request, pk):
    if request.user.is_carrier():
        carrier = getattr(request.user, "carrier_profile", None)
        issue_queryset = CarrierIssue.objects.filter(carrier=carrier)
    else:
        issue_queryset = CarrierIssue.objects.all()

    issue = get_object_or_404(
        issue_queryset.select_related("carrier__user", "order").prefetch_related("replies__author"),
        pk=pk,
    )

    reply_form = CarrierIssueReplyForm()
    if request.method == "POST" and "reply_submit" in request.POST:
        reply_form = CarrierIssueReplyForm(request.POST)
        if reply_form.is_valid():
            reply = reply_form.save(commit=False)
            reply.issue = issue
            reply.author = request.user
            reply.save()

            if request.user.is_super_admin() or request.user.is_dispatcher():
                if issue.status == CarrierIssue.Status.REPORTED:
                    issue.status = CarrierIssue.Status.UNDER_REVIEW
                    issue.save()
                if issue.carrier and issue.carrier.user:
                    Notification.objects.create(
                        user=issue.carrier.user,
                        order=issue.order,
                        message=f"{request.user.get_full_name() or request.user.username} replied to your issue: {reply.message[:120]}",
                    )
            elif request.user.is_carrier():
                review_users = User.objects.filter(role__in=[User.Role.SUPER_ADMIN, User.Role.DISPATCHER], is_active=True)
                for recipient in review_users:
                    Notification.objects.create(
                        user=recipient,
                        order=issue.order,
                        message=f"Carrier {issue.carrier.display_name} replied to issue {issue.get_category_display()}: {reply.message[:120]}",
                    )

            messages.success(request, "Reply posted.")
            return redirect("tracking:carrier_issue_detail", pk=issue.pk)

    return render(request, "tracking/carrier_issue_detail.html", {
        "issue": issue,
        "reply_form": reply_form,
    })


@role_required("super_admin", "dispatcher", "carrier", "client", "lab_staff")
def order_detail(request, pk):
    order = _get_order_for_user(request.user, pk)
    samples = order.samples.all()
    custody_events = order.custody_events.all()

    navigation_url = None
    if order.latitude is not None and order.longitude is not None:
        navigation_url = "#order-map"

    assign_form = AssignCarrierForm()

    suggested_carriers = []
    if (request.user.is_super_admin or request.user.is_dispatcher) and order.status in [Order.Status.PENDING_REVIEW, Order.Status.PENDING]:
        suggested_carriers = _suggest_carriers_for_order(order, limit=6)

    carrier_coordinates = None
    if order.carrier and order.carrier.current_latitude is not None and order.carrier.current_longitude is not None:
        carrier_coordinates = {"latitude": order.carrier.current_latitude, "longitude": order.carrier.current_longitude}

    return render(request, "tracking/order_detail.html", {
        "order": order,
        "samples": samples,
        "custody_events": custody_events,
        "assign_form": assign_form,
        "navigation_url": navigation_url,
        "carrier_coordinates": carrier_coordinates,
        "suggested_carriers": suggested_carriers,
    })


@role_required("super_admin", "dispatcher")
def order_search(request):
    """Search orders across the system for dispatchers and admins.

    Supports search by reference code, client name, requestor name/phone,
    carrier name/username and order status.
    """
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    results = Order.objects.select_related("client", "carrier").order_by("-created_at")

    if q:
        results = results.filter(
            Q(reference_code__icontains=q)
            | Q(client__name__icontains=q)
            | Q(requestor_name__icontains=q)
            | Q(requestor_phone__icontains=q)
            | Q(client__contact_name__icontains=q)
            | Q(client__contact_phone__icontains=q)
            | Q(carrier__user__username__icontains=q)
            | Q(carrier__user__first_name__icontains=q)
            | Q(carrier__user__last_name__icontains=q)
            | Q(status__icontains=q)
        )

    if status_filter:
        results = results.filter(status=status_filter)

    page = request.GET.get("page", 1)
    paginator = Paginator(results, 20)
    results = paginator.get_page(page)

    query_params = request.GET.copy()
    if "page" in query_params:
        del query_params["page"]

    return render(
        request,
        "tracking/order_search_results.html",
        {
            "query": q,
            "status_filter": status_filter,
            "statuses": Order.Status.choices,
            "results": results,
            "page_obj": results,
            "querystring": query_params.urlencode(),
        },
    )


@role_required("super_admin", "dispatcher")
def carrier_monitoring(request):
    role = _user_role(request.user)
    return render(request, "tracking/carrier_monitoring.html", {"role": role, "lab_location": settings.LAB_LOCATION})

@role_required("super_admin", "dispatcher")
def carrier_positions(request):
    carriers = Carrier.objects.filter(is_active=True).select_related("user")
    data = []
    for carrier in carriers:
        name = "Unnamed carrier"
        if carrier.user:
            name = carrier.user.get_full_name() or carrier.user.username

        order = Order.objects.filter(
            carrier=carrier,
            status__in=[
                Order.Status.ASSIGNED,
                Order.Status.ACCEPTED,
                Order.Status.EN_ROUTE_TO_CLIENT,
                Order.Status.AT_CLIENT,
                Order.Status.PICKED_UP,
                Order.Status.IN_TRANSIT,
                Order.Status.DELIVERED,
            ],
        ).order_by('-created_at').first()

        route = []
        destination = settings.LAB_LOCATION.get('name', 'Laboratory')
        if order and order.latitude is not None and order.longitude is not None:
            if order.status in [
                Order.Status.ASSIGNED,
                Order.Status.ACCEPTED,
                Order.Status.EN_ROUTE_TO_CLIENT,
                Order.Status.AT_CLIENT,
            ]:
                if carrier.current_latitude is not None and carrier.current_longitude is not None:
                    route = [
                        [carrier.current_latitude, carrier.current_longitude],
                        [order.latitude, order.longitude],
                    ]
                destination = "Pickup point"
            else:
                route = [
                    [order.latitude, order.longitude],
                    [settings.LAB_LOCATION['latitude'], settings.LAB_LOCATION['longitude']],
                ]
                destination = settings.LAB_LOCATION.get('name', 'Laboratory')

        data.append({
            "id": str(carrier.id),
            "name": name,
            "latitude": carrier.current_latitude,
            "longitude": carrier.current_longitude,
            "last_location_update": carrier.last_location_update.isoformat() if carrier.last_location_update else None,
            "status": carrier.get_status_display(),
            "order": order.reference_code if order else None,
            "order_status": order.get_status_display() if order else None,
            "order_raw_status": order.status if order else None,
            "client": order.client.name if order and order.client else None,
            "destination": destination,
            "route": route,
            "pickup_latitude": order.latitude if order else None,
            "pickup_longitude": order.longitude if order else None,
        })
    return JsonResponse({"carriers": data})


@role_required("super_admin", "dispatcher")
def order_assign_carrier(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        form = AssignCarrierForm(request.POST)
        if form.is_valid():
            carrier = form.cleaned_data["carrier"]
            if not carrier.can_be_assigned():
                messages.error(request, "Carrier already has an active job and cannot be assigned another until the current order is complete.")
                return redirect("tracking:order_detail", pk=pk)

            order.carrier = carrier
            order.status = Order.Status.ASSIGNED
            order.save()
            CustodyEvent.objects.create(order=order, event_type=CustodyEvent.EventType.CARRIER_ASSIGNED, actor=request.user, notes="Carrier assigned by dispatcher.")
            carrier.status = Carrier.Status.ON_JOB
            carrier.save()
            if carrier.user:
                Notification.objects.create(user=carrier.user, order=order, message=f"You have been assigned to order {order.reference_code}.")
            messages.success(request, "Carrier assigned.")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "dispatcher")
def order_auto_assign(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        suggested = _suggest_carriers_for_order(order, limit=1)
        if not suggested:
            messages.error(request, "No available carriers found for auto-assignment.")
            return redirect("tracking:order_detail", pk=pk)

        carrier = suggested[0]["carrier"]
        if not carrier.can_be_assigned():
            messages.error(request, "Top suggested carrier is no longer available.")
            return redirect("tracking:order_detail", pk=pk)

        order.carrier = carrier
        order.status = Order.Status.ASSIGNED
        order.save()
        CustodyEvent.objects.create(order=order, event_type=CustodyEvent.EventType.CARRIER_ASSIGNED, actor=request.user, notes="Carrier auto-assigned by dispatcher.")
        carrier.status = Carrier.Status.ON_JOB
        carrier.save()
        if carrier.user:
            Notification.objects.create(user=carrier.user, order=order, message=f"You have been assigned to order {order.reference_code}.")
        messages.success(request, f"Order auto-assigned to {carrier.display_name}.")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "carrier")
def order_accept_assignment(request, pk):
    order = _get_order_for_user(request.user, pk)
    carrier_profile = getattr(request.user, "carrier_profile", None)
    if order.carrier and carrier_profile == order.carrier and request.method == "POST":
        order.status = Order.Status.ACCEPTED
        order.save()
        CustodyEvent.objects.create(order=order, event_type=CustodyEvent.EventType.ASSIGNMENT_ACCEPTED, actor=request.user, notes="Carrier accepted assignment.")
        messages.success(request, "assignment accepted")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "carrier")
def order_start_to_client(request, pk):
    order = _get_order_for_user(request.user, pk)
    carrier_profile = getattr(request.user, "carrier_profile", None)
    if order.carrier and carrier_profile == order.carrier and request.method == "POST":
        # Only allow starting trip from ASSIGNED or ACCEPTED states.
        if order.status in [Order.Status.ASSIGNED, Order.Status.ACCEPTED]:
            order.status = Order.Status.EN_ROUTE_TO_CLIENT
            order.save()
            CustodyEvent.objects.create(order=order, event_type=CustodyEvent.EventType.STARTED_TO_CLIENT, actor=request.user, notes="Carrier began trip to client.")
            messages.success(request, "en route to client")
            return redirect("tracking:carrier_view")
        elif order.status == Order.Status.EN_ROUTE_TO_CLIENT:
            messages.info(request, "Trip already started.")
        else:
            # Prevent re-opening navigation for completed/cancelled orders
            messages.error(request, "Cannot start trip for this order (already completed or closed).")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "carrier")
def order_arrive_client(request, pk):
    order = _get_order_for_user(request.user, pk)
    carrier_profile = getattr(request.user, "carrier_profile", None)
    if order.carrier and carrier_profile == order.carrier and request.method == "POST":
        order.status = Order.Status.AT_CLIENT
        order.save()
        CustodyEvent.objects.create(order=order, event_type=CustodyEvent.EventType.ARRIVED_AT_CLIENT, actor=request.user, notes="Carrier arrived at client location.")
        messages.success(request, "arrived at client")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "carrier")
def order_mark_pickup(request, pk):
    order = _get_order_for_user(request.user, pk)
    carrier_profile = getattr(request.user, "carrier_profile", None)
    if order.carrier and carrier_profile == order.carrier and request.method == "POST":
        order.status = Order.Status.PICKED_UP
        order.save()
        CustodyEvent.objects.create(order=order, event_type=CustodyEvent.EventType.PICKED_UP, actor=request.user, notes="Carrier confirmed pickup.")
        messages.success(request, "marked picked up")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "carrier")
def sample_mark_pickup(request, pk):
    sample_queryset = Sample.objects.select_related("order")
    if request.user.is_carrier():
        carrier_profile = getattr(request.user, "carrier_profile", None)
        sample_queryset = sample_queryset.filter(order__carrier=carrier_profile)
    sample = get_object_or_404(sample_queryset, pk=pk)
    if request.method == "POST":
        sample.is_received = False
        sample.save()
        CustodyEvent.objects.create(sample=sample, order=sample.order, event_type=CustodyEvent.EventType.PICKED_UP, actor=request.user, notes="Verified at pickup via barcode scan")
        messages.success(request, f"Sample {sample.barcode} pickup recorded.")
    return redirect("tracking:order_detail", pk=sample.order.pk)


@role_required("super_admin", "carrier")
def sample_mark_delivery(request, pk):
    sample_queryset = Sample.objects.select_related("order")
    if request.user.is_carrier():
        carrier_profile = getattr(request.user, "carrier_profile", None)
        sample_queryset = sample_queryset.filter(order__carrier=carrier_profile)
    sample = get_object_or_404(sample_queryset, pk=pk)
    if request.method == "POST":
        sample.is_received = True
        sample.save()
        CustodyEvent.objects.create(sample=sample, order=sample.order, event_type=CustodyEvent.EventType.DELIVERED, actor=request.user, notes="Carrier confirmed delivery.")
        if not sample.order.samples.filter(is_received=False).exists():
            sample.order.status = Order.Status.DELIVERED
            sample.order.save()
        messages.success(request, f"Sample {sample.barcode} marked delivered.")
    return redirect("tracking:order_detail", pk=sample.order.pk)


def reports_view(request):
    return render(request, "tracking/reports.html", {})


@role_required("lab_staff")
def lab_dashboard(request):
    orders = Order.objects.filter(status=Order.Status.DELIVERED).order_by("-updated_at")
    return render(request, "tracking/lab_dashboard.html", {"orders": orders})


@role_required("super_admin", "dispatcher")
def order_create(request):
    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save()
            messages.success(request, "Order created")
            return redirect("tracking:order_detail", pk=order.pk)
    else:
        form = OrderForm()
    return render(request, "tracking/order_form.html", {"form": form})


@role_required("super_admin", "dispatcher")
def order_mark_collected(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        order.status = Order.Status.PICKED_UP
        order.save()
        messages.success(request, "Order marked collected")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "dispatcher", "carrier")
def order_mark_in_transit(request, pk):
    order = _get_order_for_user(request.user, pk)
    if request.method == "POST":
        order.status = Order.Status.IN_TRANSIT
        order.save()
        messages.success(request, "Order marked in transit")
        if request.user.is_carrier():
            return redirect("tracking:carrier_view")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "dispatcher", "carrier")
def order_mark_delivery(request, pk):
    order = _get_order_for_user(request.user, pk)
    if request.method == "POST":
        order.status = Order.Status.DELIVERED
        order.save()
        CustodyEvent.objects.create(order=order, event_type=CustodyEvent.EventType.DELIVERED, actor=request.user, notes="Delivered to lab.")

        carrier = order.carrier
        if carrier and carrier.status != Carrier.Status.AVAILABLE:
            carrier.status = Carrier.Status.AVAILABLE
            carrier.save()
            if carrier.user:
                Notification.objects.create(
                    user=carrier.user,
                    order=order,
                    message=f"Order {order.reference_code} is delivered. You are now available for new pickups.",
                )

        client_user = None
        if order.client and order.client.contact_email:
            try:
                client_user = User.objects.filter(email=order.client.contact_email).first()
            except Exception:
                client_user = None

        if client_user:
            Notification.objects.create(user=client_user, order=order, message=f"Your samples ({order.reference_code}) have been delivered.")

        messages.success(request, "marked delivered")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "dispatcher", "lab_staff")
def order_mark_received(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        order.status = Order.Status.RECEIVED
        order.save()
        CustodyEvent.objects.create(order=order, event_type=CustodyEvent.EventType.RECEIVED, actor=request.user, notes="Received at lab.")
        messages.success(request, "marked received at lab")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "dispatcher")
def order_mark_complete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        if order.status != Order.Status.RECEIVED:
            messages.error(request, "Order cannot be completed until it has been received at the lab.")
            return redirect("tracking:order_detail", pk=pk)

        order.status = Order.Status.COMPLETED
        order.save()

        # Free up the carrier so they can accept new jobs
        carrier = order.carrier
        if carrier and carrier.status != Carrier.Status.AVAILABLE:
            carrier.status = Carrier.Status.AVAILABLE
            carrier.save()
            # Notify the carrier they are now available
            if carrier.user:
                Notification.objects.create(
                    user=carrier.user,
                    order=order,
                    message=f"Order {order.reference_code} is complete. You are now available for new pickups.",
                )

        messages.success(request, "Order marked complete. Carrier is now available for new jobs.")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "dispatcher", "carrier", "client", "lab_staff")
def notification_mark_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.is_read = True
    n.save()
    return redirect(request.GET.get("next") or "tracking:dashboard")


@csrf_protect
def mark_all_notifications_read(request):
    """Mark all notifications as read for the current user"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)
    
    count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"success": True, "message": f"Marked {count} notifications as read", "count": count})


@csrf_protect
def clear_all_notifications(request):
    """Delete all notifications for the current user"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)
    
    count, _ = Notification.objects.filter(user=request.user).delete()
    return JsonResponse({"success": True, "message": f"Cleared {count} notifications", "count": count})


@role_required("super_admin", "dispatcher")
def order_add_sample(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        form = SampleForm(request.POST)
        if form.is_valid():
            s = form.save(commit=False)
            s.order = order
            s.save()
            messages.success(request, "Sample added")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "dispatcher")
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        order.status = Order.Status.CANCELLED
        order.save()

        # Free up the carrier so they can take new jobs
        carrier = order.carrier
        if carrier and carrier.status != Carrier.Status.AVAILABLE:
            carrier.status = Carrier.Status.AVAILABLE
            carrier.save()
            if carrier.user:
                Notification.objects.create(
                    user=carrier.user,
                    order=order,
                    message=f"Order {order.reference_code} was cancelled. You are now available for new pickups.",
                )

        messages.success(request, "Order cancelled. Carrier is now available for new jobs.")
    return redirect("tracking:order_detail", pk=pk)


@role_required("super_admin", "dispatcher", "carrier")
def verify_samples_collection(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        barcodes_text = request.POST.get("barcodes", "")
        barcodes = [b.strip() for b in barcodes_text.splitlines() if b.strip()]
        matched_any = False
        for code in barcodes:
            try:
                s = Sample.objects.get(barcode=code, order=order)
                s.is_received = True
                s.save()
                CustodyEvent.objects.create(sample=s, order=order, event_type=CustodyEvent.EventType.PICKED_UP, actor=request.user, notes="Collected at pickup.")
                matched_any = True
            except Sample.DoesNotExist:
                continue
        if matched_any:
            order.status = Order.Status.PICKED_UP
            order.save()
            messages.success(request, "Samples verified")
        else:
            messages.error(request, "No matching barcodes found")
    return redirect("tracking:order_detail", pk=pk)


def api_notifications(request):
    from django.http import JsonResponse
    from django.urls import reverse
    
    if not request.user.is_authenticated:
        return JsonResponse({"unread": 0, "notifications": []}, status=401)
    
    unread = Notification.objects.filter(user=request.user, is_read=False).count()
    recent = Notification.objects.filter(user=request.user).order_by("-created_at")[:10]
    
    data = []
    for n in recent:
        data.append({
            "pk": str(n.pk),
            "message": n.message,
            "is_read": n.is_read,
            "created_at_seconds": int((timezone.now() - n.created_at).total_seconds()),
            "mark_url": reverse("tracking:notification_mark_read", args=[n.pk])
        })
        
    return JsonResponse({
        "unread": unread,
        "notifications": data
    })


# ===== Facility Management Views =====

@role_required("super_admin", "dispatcher")
def facility_list(request):
    """List all facilities with filtering and search."""
    facilities = Facility.objects.all().order_by("name")
    
    # Search functionality
    search = request.GET.get("search", "").strip()
    if search:
        facilities = facilities.filter(
            Q(name__icontains=search) | 
            Q(address__icontains=search) | 
            Q(contact_name__icontains=search) | 
            Q(contact_phone__icontains=search)
        )
    
    # Filter by active status
    status_filter = request.GET.get("status", "")
    if status_filter == "active":
        facilities = facilities.filter(is_active=True)
    elif status_filter == "inactive":
        facilities = facilities.filter(is_active=False)
    
    context = {
        "facilities": facilities,
        "search": search,
        "status_filter": status_filter,
        "total_count": Facility.objects.count(),
        "active_count": Facility.objects.filter(is_active=True).count(),
    }
    
    return render(request, "tracking/facility_list.html", context)


@role_required("super_admin", "dispatcher")
def facility_create(request):
    """Create a new facility."""
    if request.method == "POST":
        form = FacilityForm(request.POST)
        if form.is_valid():
            facility = form.save()
            messages.success(request, f"Facility '{facility.name}' created successfully.")
            return redirect("tracking:facility_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = FacilityForm()
    
    context = {
        "form": form,
        "action": "Create",
    }
    
    return render(request, "tracking/facility_form.html", context)


@role_required("super_admin", "dispatcher")
def facility_update(request, pk):
    """Edit an existing facility."""
    facility = get_object_or_404(Facility, pk=pk)
    
    if request.method == "POST":
        form = FacilityForm(request.POST, instance=facility)
        if form.is_valid():
            facility = form.save()
            messages.success(request, f"Facility '{facility.name}' updated successfully.")
            return redirect("tracking:facility_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = FacilityForm(instance=facility)
    
    context = {
        "form": form,
        "facility": facility,
        "action": "Update",
    }
    
    return render(request, "tracking/facility_form.html", context)


@role_required("super_admin", "dispatcher")
def facility_delete(request, pk):
    """Delete a facility."""
    facility = get_object_or_404(Facility, pk=pk)
    
    if request.method == "POST":
        facility_name = facility.name
        facility.delete()
        messages.success(request, f"Facility '{facility_name}' deleted successfully.")
        return redirect("tracking:facility_list")
    
    context = {
        "facility": facility,
    }
    
    return render(request, "tracking/facility_confirm_delete.html", context)


