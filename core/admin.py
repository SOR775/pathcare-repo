from django.contrib import admin
from .models import Facility, SystemSetting


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'contact_phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'address', 'contact_name', 'contact_phone', 'contact_email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'address')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'description': 'GPS coordinates for routing to main lab'
        }),
        ('Contact', {
            'fields': ('contact_name', 'contact_phone', 'contact_email')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'created_at')
    search_fields = ('key',)
    readonly_fields = ('created_at',)
