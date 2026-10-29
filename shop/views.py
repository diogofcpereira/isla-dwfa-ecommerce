# shop/views.py
from django.db.models import F, Prefetch, Sum
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import ProductFilter
from .models import Category, Customer, Order, OrderItem, Product
from .permissions import (IsGestorOrReadOnly, IsItemOwnerOrGestor,
                          IsOwnerOrGestor, is_gestor)
from .serializers import (CategorySerializer, OrderItemSerializer,
                          OrderSerializer, ProductSerializer)
from .services import add_item, pay_order


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    # Catálogo público: qualquer visitante pode ver as categorias (decisão consciente).
    permission_classes = [AllowAny]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category")
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    search_fields = ["name", "sku"]
    ordering_fields = ["price", "name", "created_at"]
    ordering = ["name"]
    # Leitura pública (catálogo); criar, alterar e apagar só para gestores.
    permission_classes = [IsGestorOrReadOnly]


class OrderItemViewSet(viewsets.ModelViewSet):
    # O router usa este atributo para dar nome às rotas; os dados vêm de get_queryset.
    queryset = OrderItem.objects.select_related("product")
    serializer_class = OrderItemSerializer
    filterset_fields = ["order"]
    ordering = ["id"]
    permission_classes = [IsAuthenticated, IsItemOwnerOrGestor]

    def get_queryset(self):
        qs = OrderItem.objects.select_related("product", "order__customer")
        if is_gestor(self.request.user):
            return qs                                   # gestores veem todas as linhas
        # Um cliente só vê linhas das suas encomendas; as outras dão 404.
        return qs.filter(order__customer__user_id=self.request.user.id)

    def perform_create(self, serializer):
        # O serializer já confirmou que a encomenda é do utilizador (validate_order).
        data = serializer.validated_data
        serializer.instance = add_item(data["order"], data["product"], data["quantity"])


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    filterset_fields = ["status", "customer"]
    ordering_fields = ["created_at", "total"]
    ordering = ["-created_at"]
    permission_classes = [IsAuthenticated, IsOwnerOrGestor]

    def get_queryset(self):
        qs = Order.objects.select_related("customer__user")
        if not is_gestor(self.request.user):
            # Camada 1: um cliente só "vê" as suas encomendas.
            # As outras dão 404 — nem se confirma que existem.
            qs = qs.filter(customer__user_id=self.request.user.id)
        items = OrderItem.objects.select_related("product")
        line = F("items__quantity") * F("items__unit_price")
        return (qs.prefetch_related(Prefetch("items", queryset=items))
                  .annotate(total=Sum(line)))

    def perform_create(self, serializer):
        # O dono vem sempre do utilizador autenticado, nunca do JSON enviado.
        # get_or_create: um utilizador sem perfil de cliente (ex.: um gestor) ganha um.
        customer, _ = Customer.objects.get_or_create(user=self.request.user)
        serializer.save(customer=customer)

    @extend_schema(
        request=None,
        responses={200: OrderSerializer,
                   409: OpenApiResponse(description="A encomenda já não está pendente.")})
    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        # get_object() aplica o filtro do get_queryset (404 se não for tua)
        # e corre o IsOwnerOrGestor.has_object_permission.
        pay_order(self.get_object())
        order = self.get_queryset().get(pk=pk)   # relê com o total calculado
        return Response(self.get_serializer(order).data)