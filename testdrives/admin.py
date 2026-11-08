from django.contrib import admin

from .models import TestDrive


@admin.register(TestDrive)
class TestDriveAdmin(admin.ModelAdmin):
    list_display = ["car", "customer", "scheduled_for", "status"]
    list_filter = ["status"]
    search_fields = ["car__model", "customer__user__username"]
    list_select_related = ["car__brand", "customer__user"]
