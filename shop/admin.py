# Register your models here.
from django.contrib import admin

from .models import Category, Customer, Order, OrderItem, Payment, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "category", "price", "stock", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["sku", "name"]
    list_select_related = ["category"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["user", "phone"]
    search_fields = ["user__username", "user__email"]
    list_select_related = ["user"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ["product"]


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