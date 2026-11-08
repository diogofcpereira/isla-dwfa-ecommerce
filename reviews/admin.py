from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["car", "customer", "rating", "status", "created_at"]
    list_filter = ["status", "rating"]
    search_fields = ["comment", "car__model", "customer__user__username"]
    list_select_related = ["car__brand", "customer__user"]
