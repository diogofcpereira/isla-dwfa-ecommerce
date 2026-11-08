from rest_framework import serializers

from shop.models import Customer, Order, OrderItem

from .models import Review

# Só conta como compra uma encomenda paga ou já entregue.
BOUGHT = [Order.Status.PAID, Order.Status.DELIVERED]


class ReviewSerializer(serializers.ModelSerializer):
    car_name = serializers.CharField(source="car.name", read_only=True)
    author = serializers.CharField(source="customer.user.username", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "car",
            "car_name",
            "customer",
            "author",
            "rating",
            "comment",
            "status",
            "status_display",
            "created_at",
        ]
        # O autor vem do login e o estado só muda em /moderate/ (gestor).
        read_only_fields = ["customer", "status", "created_at"]

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            fields["car"].read_only = True  # uma avaliação não muda de viatura
        return fields

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("A nota vai de 1 a 5.")
        return value

    def validate(self, attrs):
        if self.instance is not None:
            return attrs
        customer = Customer.objects.filter(user=self.context["request"].user).first()
        car = attrs["car"]
        bought = OrderItem.objects.filter(
            car=car, order__customer=customer, order__status__in=BOUGHT
        ).exists()
        if not bought:
            raise serializers.ValidationError(
                {"car": "Só pode avaliar uma viatura quem a comprou (encomenda paga ou entregue)."}
            )
        if Review.objects.filter(car=car, customer=customer).exists():
            raise serializers.ValidationError(
                {"car": "Já avaliaste esta viatura: edita a tua avaliação."}
            )
        return attrs


class ModerationSerializer(serializers.Serializer):
    """Corpo de POST /reviews/{id}/moderate/."""

    status = serializers.ChoiceField(
        choices=[Review.Status.APPROVED, Review.Status.HIDDEN],
    )
