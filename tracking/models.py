

import uuid

from django.conf import settings
from django.db import models


class UserRole(models.TextChoices):
    DISPATCH = "dispatch", "Dispatch"
    CARRIER = "carrier", "Carrier"
    CLIENT = "client", "Client"


class Client(models.Model):
    """A hospital, clinic, or facility that requests sample pickups."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=32)
    contact_email = models.EmailField(blank=True)
    address = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    default_facility = models.ForeignKey(
        'core.Facility',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients',
        help_text="Default facility for this client's pickups"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    """A vehicle assigned to a carrier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle_type = models.CharField(max_length=64, blank=True)
    vehicle_plate = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vehicle_type} {self.vehicle_plate}".strip() or "Vehicle pending"


class Carrier(models.Model):
    """A driver who picks up and delivers samples."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        ON_JOB = "on_job", "On job"
        OFFLINE = "offline", "Offline"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carrier_profile",
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=32)
    vehicle = models.OneToOneField(
        'Vehicle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carrier',
    )
    vehicle_type = models.CharField(max_length=64, blank=True)
    vehicle_plate = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.AVAILABLE)
    current_latitude = models.FloatField(null=True, blank=True)
    current_longitude = models.FloatField(null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    @property
    def display_name(self):
        try:
            user = self.user
        except Exception:
            return "Unnamed carrier"

        if user is None:
            return "Unnamed carrier"

        return user.get_full_name() or user.username

    def __str__(self):
        return self.display_name

    @property
    def vehicle_display(self):
        if self.vehicle:
            return str(self.vehicle)
        if self.vehicle_type or self.vehicle_plate:
            return f"{self.vehicle_type} {self.vehicle_plate}".strip()
        return "Vehicle pending"

    def has_active_order(self):
        return self.orders.filter(status__in=Order.active_statuses()).exists()

    def can_be_assigned(self):
        return self.status == self.Status.AVAILABLE and not self.has_active_order()


class CarrierIssue(models.Model):
    class Category(models.TextChoices):
        ACCIDENT = "accident", "Accident"
        PUNCTURE = "puncture", "Puncture"
        DELAY = "delay", "Delay"
        VEHICLE = "vehicle", "Vehicle issue"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        REPORTED = "reported", "Reported"
        UNDER_REVIEW = "under_review", "Under review"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    carrier = models.ForeignKey(
        "Carrier",
        on_delete=models.CASCADE,
        related_name="issues",
    )
    order = models.ForeignKey(
        "Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issues",
    )
    category = models.CharField(max_length=24, choices=Category.choices, default=Category.OTHER)
    description = models.TextField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.REPORTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_category_display()} issue by {self.carrier}"


class CarrierIssueReply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(
        CarrierIssue,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="issue_replies",
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply by {self.author} on {self.issue}"


class Order(models.Model):
    """A pickup request. One order can bundle several samples from the same client visit."""

    class Priority(models.TextChoices):
        ROUTINE = "routine", "Routine"
        URGENT = "urgent", "Priority"
        STAT = "stat", "STAT (immediate)"

    class Status(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending review"
        PENDING = "pending", "Pending assignment"
        ASSIGNED = "assigned", "Assigned to carrier"
        ACCEPTED = "accepted", "Accepted by carrier"
        EN_ROUTE_TO_CLIENT = "en_route_client", "En route to client"
        AT_CLIENT = "at_client", "Arrived at client"
        PICKED_UP = "picked_up", "Picked up"
        IN_TRANSIT = "in_transit", "In transit"
        DELIVERED = "delivered", "Delivered to lab"
        RECEIVED = "received", "Received at lab"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_code = models.CharField(max_length=32, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="orders")
    facility = models.ForeignKey(
        'core.Facility',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        help_text="Facility for this pickup (defaults to client's default facility)"
    )
    carrier = models.ForeignKey(
        Carrier, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.ROUTINE)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    requested_pickup_time = models.DateTimeField(null=True, blank=True)
    samples_ready_at = models.DateTimeField(null=True, blank=True)
    requestor_name = models.CharField(max_length=255, blank=True)
    requestor_phone = models.CharField(max_length=32, blank=True)
    reception_details = models.CharField(max_length=255, blank=True)
    parking_notes = models.CharField(max_length=255, blank=True)
    security_instructions = models.CharField(max_length=255, blank=True)
    pickup_address = models.CharField(max_length=255, blank=True)
    distance_to_lab_km = models.FloatField(null=True, blank=True)
    estimated_pickup_minutes = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.reference_code

    @classmethod
    def active_statuses(cls):
        return [
            cls.Status.ASSIGNED,
            cls.Status.ACCEPTED,
            cls.Status.EN_ROUTE_TO_CLIENT,
            cls.Status.AT_CLIENT,
            cls.Status.PICKED_UP,
            cls.Status.IN_TRANSIT,
            cls.Status.DELIVERED,
            cls.Status.RECEIVED,
        ]

    @classmethod
    def final_statuses(cls):
        return [cls.Status.COMPLETED, cls.Status.CANCELLED]

    def is_active(self):
        return self.status not in self.final_statuses()

    def save(self, *args, **kwargs):
        if not self.reference_code:
            self.reference_code = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class Sample(models.Model):
    """An individual sample container belonging to an order."""

    class SampleType(models.TextChoices):
        BLOOD = "blood", "Blood"
        URINE = "urine", "Urine"
        TISSUE = "tissue", "Tissue"
        SWAB = "swab", "Swab"
        OTHER = "other", "Other"

    class ColdChain(models.TextChoices):
        AMBIENT = "ambient", "Ambient"
        REFRIGERATED = "refrigerated", "2–8°C (Refrigerated)"
        FROZEN = "frozen", "Frozen"
        DRY_ICE = "dry_ice", "Dry Ice"
        LIQUID_NITROGEN = "liquid_nitrogen", "Liquid Nitrogen"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, related_name="samples", null=True, blank=True)
    barcode = models.CharField(max_length=64, unique=True)
    sample_type = models.CharField(max_length=16, choices=SampleType.choices)
    cold_chain_requirement = models.CharField(
        max_length=16, choices=ColdChain.choices, default=ColdChain.AMBIENT
    )
    is_damaged = models.BooleanField(default=False)
    is_received = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.barcode} ({self.get_sample_type_display()})"


class CustodyEvent(models.Model):
    """
    Immutable log entry recording every handoff of a sample.
    This is the chain-of-custody audit trail - treat as append-only,
    never update or delete existing rows.
    """

    class EventType(models.TextChoices):
        ORDER_CREATED = "order_created", "Order created"
        REQUEST_APPROVED = "request_approved", "Request approved"
        CARRIER_ASSIGNED = "carrier_assigned", "Carrier assigned"
        ASSIGNMENT_ACCEPTED = "assignment_accepted", "Assignment accepted"
        STARTED_TO_CLIENT = "started_to_client", "Started trip to client"
        ARRIVED_AT_CLIENT = "arrived_at_client", "Arrived at client"
        PICKED_UP = "picked_up", "Picked up from client"
        TEMPERATURE_CHECK = "temp_check", "Temperature check"
        DEPARTED = "departed", "Departed (in transit)"
        DELIVERED = "delivered", "Delivered to lab"
        RECEIVED = "received", "Received at lab"
        COMPLETED = "completed", "Order completed"
        EXCEPTION = "exception", "Exception (delay, damage, etc.)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sample = models.ForeignKey(
        Sample, on_delete=models.SET_NULL, related_name="custody_events", null=True, blank=True
    )
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, related_name="custody_events", null=True, blank=True)
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="custody_events"
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    temperature_celsius = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    photo = models.ImageField(upload_to="custody_photos/", null=True, blank=True)
    signature = models.ImageField(upload_to="signatures/", null=True, blank=True)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        sample_ref = self.sample.barcode if self.sample_id and self.sample else "no sample"
        return f"{self.get_event_type_display()} - {sample_ref} @ {self.timestamp}"


class Notification(models.Model):
    """Simple in-app notification for users about order events."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    order = models.ForeignKey(
        "Order", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message[:50]
