from django.contrib import admin

from .models import Brand, Car, Customer, Order, OrderItem, Payment


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "brand",
        "model",
        "version",
        "year",
        "fuel",
        "price",
        "stock",
        "is_active",
    ]
    list_filter = ["brand", "fuel", "is_active"]
    search_fields = ["code", "model", "version", "brand__name"]
    list_select_related = ["brand"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["user", "phone"]
    search_fields = ["user__username", "user__email"]
    list_select_related = ["user"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ["car"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["customer__user__username"]
    list_select_related = ["customer__user"]
    inlines = [OrderItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["order", "method", "amount", "paid_at"]
    list_select_related = ["order"]
