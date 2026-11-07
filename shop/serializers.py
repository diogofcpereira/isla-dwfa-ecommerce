# shop/serializers.py
import datetime

from rest_framework import serializers

from .models import Brand, Car, Order, OrderItem, Payment
from .permissions import is_gestor


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug"]


class CarSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    fuel_display = serializers.CharField(source="get_fuel_display", read_only=True)

    class Meta:
        model = Car
        fields = [
            "id",
            "brand",
            "brand_name",
            "code",
            "model",
            "version",
            "year",
            "fuel",
            "fuel_display",
            "price",
            "stock",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("O preço tem de ser positivo.")
        return value

    def validate_year(self, value):
        # Aceita o modelo do ano seguinte (é comum no mercado automóvel).
        latest = datetime.date.today().year + 1
        if not 1990 <= value <= latest:
            raise serializers.ValidationError(f"O ano tem de estar entre 1990 e {latest}.")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    car_name = serializers.CharField(source="car.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "order", "car", "car_name", "quantity", "unit_price"]
        # O preço é copiado da viatura pelo servidor (services.add_item).
        read_only_fields = ["unit_price"]

    def validate_order(self, order):
        """Um cliente só pode acrescentar linhas às suas encomendas."""
        request = self.context.get("request")
        if request is None:  # uso fora de uma view (ex.: shell)
            return order
        user = request.user
        if not is_gestor(user) and order.customer.user_id != user.id:
            # Mesma mensagem que para uma encomenda inexistente: não revela que ela existe.
            raise serializers.ValidationError("Encomenda não encontrada.")
        return order

    def validate_car(self, car):
        if not car.is_active:
            raise serializers.ValidationError("Esta viatura já não está à venda.")
        return car

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("A quantidade tem de ser pelo menos 1.")
        return value

    def validate(self, attrs):
        car = attrs.get("car") or getattr(self.instance, "car", None)
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", 0))
        if car and quantity > car.stock:
            raise serializers.ValidationError({"quantity": f"Só há {car.stock} em stock."})
        return attrs


class OrderLineSerializer(serializers.ModelSerializer):
    """Uma linha dentro de POST /orders/: só se envia a viatura e a quantidade."""

    car_name = serializers.CharField(source="car.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "car", "car_name", "quantity", "unit_price"]
        read_only_fields = ["unit_price"]

    def validate_car(self, car):
        if not car.is_active:
            raise serializers.ValidationError("Esta viatura já não está à venda.")
        return car

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("A quantidade tem de ser pelo menos 1.")
        return value

    def validate(self, attrs):
        # Primeira verificação, para dar um 400 claro; a definitiva é no
        # services.add_item, com a viatura bloqueada (aí falha com 409).
        if attrs["quantity"] > attrs["car"].stock:
            raise serializers.ValidationError({"quantity": f"Só há {attrs['car'].stock} em stock."})
        return attrs


class OrderSerializer(serializers.ModelSerializer):
    # Na criação, as linhas vêm no mesmo pedido; depois só se leem.
    items = OrderLineSerializer(many=True, allow_empty=False)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "customer", "status", "created_at", "items", "total"]
        # Tudo o que é o servidor a decidir:
        # - customer: vem do utilizador autenticado (OrderViewSet.perform_create);
        # - status: só muda através de ações como /pay/;
        # - created_at: data do servidor.
        read_only_fields = ["customer", "status", "created_at"]

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            # Numa encomenda que já existe, as linhas mudam em /order-items/, não aqui.
            fields["items"].read_only = True
        return fields

    def validate_items(self, lines):
        cars = [line["car"].pk for line in lines]
        if len(cars) != len(set(cars)):
            # Sem isto, a UniqueConstraint uq_orderitem_order_car dava um 500.
            raise serializers.ValidationError(
                "A mesma viatura aparece em duas linhas: junta-as e aumenta a quantidade."
            )
        return lines


class PaySerializer(serializers.Serializer):
    """Corpo de POST /orders/{id}/pay/."""

    method = serializers.ChoiceField(choices=Payment.Method.choices)