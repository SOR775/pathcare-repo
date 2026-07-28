from django.contrib import admin

from .models import Carrier, Client, CustodyEvent, Order, Sample


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_phone", "default_facility", "is_active", "created_at")
    search_fields = ("name", "contact_phone", "contact_email", "default_facility__name")
    list_filter = ("is_active", "default_facility")
    readonly_fields = ("id", "created_at")
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'contact_name', 'contact_phone', 'contact_email')
        }),
        ('Location', {
            'fields': ('address', 'latitude', 'longitude')
        }),
        ('Facility', {
            'fields': ('default_facility',),
            'description': 'Default facility for this client\'s pickups (can be overridden per order)'
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        })
    )


@admin.register(Carrier)
class CarrierAdmin(admin.ModelAdmin):
    list_display = ("__str__", "phone", "status", "vehicle_plate", "is_active")
    list_filter = ("status", "is_active")
    search_fields = ("user__username", "user__first_name", "user__last_name", "phone")


class SampleInline(admin.TabularInline):
    model = Sample
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference_code", "client", "facility", "carrier", "priority", "status", "created_at")
    list_filter = ("status", "priority", "facility")
    search_fields = ("reference_code", "client__name", "facility__name")
    inlines = [SampleInline]
    readonly_fields = ("reference_code", "created_at", "updated_at")
    
    fieldsets = (
        ('Order Details', {
            'fields': ('id', 'reference_code', 'client', 'carrier', 'priority', 'status')
        }),
        ('Facility & Routing', {
            'fields': ('facility', 'pickup_address', 'latitude', 'longitude', 'distance_to_lab_km', 'estimated_pickup_minutes'),
            'description': 'If facility is empty, client\'s default facility will be used'
        }),
        ('Pickup Information', {
            'fields': ('requested_pickup_time', 'samples_ready_at', 'requestor_name', 'requestor_phone')
        }),
        ('Site Details', {
            'fields': ('reception_details', 'parking_notes', 'security_instructions')
        }),
        ('Additional', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ("barcode", "order", "sample_type", "cold_chain_requirement", "is_received", "is_damaged")
    list_filter = ("sample_type", "cold_chain_requirement", "is_received", "is_damaged")
    search_fields = ("barcode", "order__reference_code")


@admin.register(CustodyEvent)
class CustodyEventAdmin(admin.ModelAdmin):
    list_display = ("sample", "event_type", "actor", "timestamp")
    list_filter = ("event_type",)
    search_fields = ("sample__barcode", "order__reference_code")
    readonly_fields = [f.name for f in CustodyEvent._meta.fields]  # append-only audit log

    def has_change_permission(self, request, obj=None):
        return False  # custody events should never be edited, only created

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return request.user.has_perm("tracking.delete_custodyevent") or request.user.has_perm("tracking.delete_order")
