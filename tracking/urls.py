from django.urls import path

from . import views

app_name = "tracking"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("lab-dashboard/", views.lab_dashboard, name="lab_dashboard"),
    path("orders/new/", views.order_create, name="order_create"),
    path("orders/<uuid:pk>/", views.order_detail, name="order_detail"),
    path("orders/search/", views.order_search, name="order_search"),
    path("orders/<uuid:pk>/assign-carrier/", views.order_assign_carrier, name="order_assign_carrier"),
    path("orders/<uuid:pk>/auto-assign/", views.order_auto_assign, name="order_auto_assign"),
    path("carrier-location/update/", views.update_carrier_location, name="update_carrier_location"),
    path("carrier-positions/", views.carrier_positions, name="carrier_positions"),
    path("orders/<uuid:pk>/approve-request/", views.order_approve_request, name="order_approve_request"),
    path("orders/<uuid:pk>/accept-assignment/", views.order_accept_assignment, name="order_accept_assignment"),
    path("orders/<uuid:pk>/start-to-client/", views.order_start_to_client, name="order_start_to_client"),
    path("orders/<uuid:pk>/arrive-client/", views.order_arrive_client, name="order_arrive_client"),
    path("orders/<uuid:pk>/mark-pickup/", views.order_mark_pickup, name="order_mark_pickup"),
    path("orders/<uuid:pk>/mark-collected/", views.order_mark_collected, name="order_mark_collected"),
    path("orders/<uuid:pk>/mark-in-transit/", views.order_mark_in_transit, name="order_mark_in_transit"),
    path("orders/<uuid:pk>/mark-delivery/", views.order_mark_delivery, name="order_mark_delivery"),
    path("orders/<uuid:pk>/mark-received/", views.order_mark_received, name="order_mark_received"),
    path("orders/<uuid:pk>/mark-complete/", views.order_mark_complete, name="order_mark_complete"),
    path("notifications/<uuid:pk>/mark-read/", views.notification_mark_read, name="notification_mark_read"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("notifications/clear-all/", views.clear_all_notifications, name="clear_all_notifications"),
    path("orders/<uuid:pk>/add-sample/", views.order_add_sample, name="order_add_sample"),
    path("orders/<uuid:pk>/cancel/", views.order_cancel, name="order_cancel"),
    path("samples/<uuid:pk>/pickup/", views.sample_mark_pickup, name="sample_mark_pickup"),
    path("samples/<uuid:pk>/deliver/", views.sample_mark_delivery, name="sample_mark_delivery"),
    path("orders/<uuid:pk>/verify-samples/", views.verify_samples_collection, name="verify_samples_collection"),
    path("clients/", views.client_list, name="client_list"),
    path("clients/new/", views.client_create, name="client_create"),
    path("clients/request-pickup/", views.client_request_pickup, name="client_request_pickup"),
    path("carriers/", views.carrier_list, name="carrier_list"),
    path("carriers/new/", views.carrier_create, name="carrier_create"),
    path("carrier-view/", views.carrier_view, name="carrier_view"),
    path("carrier/issues/", views.carrier_issue_list, name="carrier_issue_list"),
    path("carrier/issues/<uuid:pk>/", views.carrier_issue_detail, name="carrier_issue_detail"),
    path("carrier-monitoring/", views.carrier_monitoring, name="carrier_monitoring"),
    path("reports/", views.reports_view, name="reports_view"),
    path("api/notifications/", views.api_notifications, name="api_notifications"),
    # Facility management
    path("facilities/", views.facility_list, name="facility_list"),
    path("facilities/new/", views.facility_create, name="facility_create"),
    path("facilities/<uuid:pk>/edit/", views.facility_update, name="facility_update"),
    path("facilities/<uuid:pk>/delete/", views.facility_delete, name="facility_delete"),
]





