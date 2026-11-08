from django.contrib import admin

from .models import Delivery


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ["order", "status", "scheduled_for", "delivered_at"]
    list_filter = ["status"]
    search_fields = ["address", "order__customer__user__username"]
    list_select_related = ["order"]