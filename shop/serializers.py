# shop/serializers.py
from rest_framework import serializers

from .models import Category, Order, OrderItem, Product
from .permissions import is_gestor


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "category", "category_name", "sku", "name",
                  "price", "stock", "is_active", "created_at"]
        read_only_fields = ["created_at"]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("O preço tem de ser positivo.")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "order", "product", "product_name",
                  "quantity", "unit_price"]
        # O preço é copiado do produto pelo servidor (services.add_item).
        read_only_fields = ["unit_price"]

    def validate_order(self, order):
        """Um cliente só pode acrescentar linhas às suas encomendas."""
        request = self.context.get("request")
        if request is None:                      # uso fora de uma view (ex.: shell)
            return order
        user = request.user
        if not is_gestor(user) and order.customer.user_id != user.id:
            # Mesma mensagem que para uma encomenda inexistente: não revela que ela existe.
            raise serializers.ValidationError("Encomenda não encontrada.")
        return order

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("A quantidade tem de ser pelo menos 1.")
        return value

    def validate(self, attrs):
        product = attrs.get("product") or getattr(self.instance, "product", None)
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", 0))
        if product and quantity > product.stock:
            raise serializers.ValidationError(
                {"quantity": f"Só há {product.stock} em stock."})
        return attrs


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "customer", "status", "created_at", "items", "total"]
        # Tudo o que é o servidor a decidir:
        # - customer: vem do utilizador autenticado (OrderViewSet.perform_create);
        # - status: só muda através de ações como /pay/;
        # - created_at: data do servidor.
        read_only_fields = ["customer", "status", "created_at"]