
# Create your views here.
from django.db.models import F, Prefetch, Sum
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.permissions import IsAuthenticated
from shop.permissions import IsOwnerOrGestor, is_gestor

from .filters import ProductFilter
from .models import Category, Order, OrderItem, Product
from .serializers import CategorySerializer, OrderItemSerializer, OrderSerializer, ProductSerializer
from .services import add_item, pay_order
from shop.permissions import IsGestorOrReadOnly


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    permission_classes = [AllowAny]   # Catálogo público: qualquer visitante pode ver as categorias


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category")
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    search_fields = ["name", "sku"]
    ordering_fields = ["price", "name", "created_at"]
    ordering = ["name"]
    permission_classes = [IsGestorOrReadOnly]


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.select_related("product")
    serializer_class = OrderItemSerializer
    filterset_fields = ["order"]
    ordering = ["id"]

    def perform_create(self, serializer):
        data = serializer.validated_data
        serializer.instance = add_item(data["order"], data["product"], data["quantity"])


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    filterset_fields = ["status", "customer"]
    ordering_fields = ["created_at", "total"]
    ordering = ["-created_at"]

    def get_queryset(self):
        items = OrderItem.objects.select_related("product")
        line = F("items__quantity") * F("items__unit_price")
        return (Order.objects.select_related("customer__user")
                .prefetch_related(Prefetch("items", queryset=items))
                .annotate(total=Sum(line)))

    @extend_schema(
        request=None,
        responses={200: OrderSerializer,
                   409: OpenApiResponse(description="A encomenda já não está pendente.")})
    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        pay_order(self.get_object())
        order = self.get_queryset().get(pk=pk)   # relê com o total calculado
        return Response(self.get_serializer(order).data)