from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from shop.models import Order

from .models import Delivery


class DeliverySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    customer = serializers.IntegerField(source="order.customer_id", read_only=True)
    # M2 (extra): o mesmo critério do ?overdue=true, para a SPA marcar a linha.
    is_overdue = serializers.SerializerMethodField()

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
            "is_overdue",
            "created_at",
        ]
        # O estado só muda pelas ações /ship/ e /complete/ (services.py).
        read_only_fields = ["status", "delivered_at", "created_at"]
        # M2: a mensagem da OneToOne em português (era "delivery with this order already
        # exists."), porque a SPA mostra-a tal e qual ao lado do campo da encomenda.
        extra_kwargs = {
            "order": {
                "validators": [
                    UniqueValidator(
                        queryset=Delivery.objects.all(),
                        message="Esta encomenda já tem uma entrega.",
                    )
                ]
            }
        }

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            # Numa entrega que já existe não se troca de encomenda.
            fields["order"].read_only = True
        return fields

    def get_is_overdue(self, delivery) -> bool:
        return (
            delivery.status != Delivery.Status.DELIVERED and delivery.scheduled_for < timezone.now()
        )

    def validate_order(self, order):
        if order.status != Order.Status.PAID:
            raise serializers.ValidationError("Só se agenda a entrega de uma encomenda paga.")
        return order

    def validate_scheduled_for(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("A data da entrega tem de ser no futuro.")
        return value


class DeliverySummarySerializer(serializers.Serializer):
    """GET /deliveries/summary/: quantas entregas há em cada estado e quantas estão em atraso."""

    scheduled = serializers.IntegerField(help_text="Agendadas.")
    in_transit = serializers.IntegerField(help_text="Em trânsito.")
    delivered = serializers.IntegerField(help_text="Entregues.")
    overdue = serializers.IntegerField(help_text="Por entregar e com a data prevista já passada.")
