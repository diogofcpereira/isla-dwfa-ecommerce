from django.utils import timezone
from rest_framework import serializers

from shop.models import Order

from .models import Delivery


class DeliverySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    customer = serializers.IntegerField(source="order.customer_id", read_only=True)

    class Meta:
        model = Delivery
        fields = [
            "id",
            "order",
            "customer",
            "status",
            "status_display",
            "scheduled_for",
            "address",
            "notes",
            "delivered_at",
            "created_at",
        ]
        # O estado só muda pelas ações /ship/ e /complete/ (services.py).
        read_only_fields = ["status", "delivered_at", "created_at"]

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            # Numa entrega que já existe não se troca de encomenda.
            fields["order"].read_only = True
        return fields

    def validate_order(self, order):
        if order.status != Order.Status.PAID:
            raise serializers.ValidationError("Só se agenda a entrega de uma encomenda paga.")
        return order

    def validate_scheduled_for(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("A data da entrega tem de ser no futuro.")
        return value