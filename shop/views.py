# shop/views.py
from django.db.models import F, Prefetch, Sum
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import CarFilter
from .models import Brand, Car, Customer, Order, OrderItem
from .permissions import IsGestorOrReadOnly, IsItemOwnerOrGestor, IsOwnerOrGestor, is_gestor
from .serializers import (
    BrandSerializer,
    CarSerializer,
    OrderItemSerializer,
    OrderSerializer,
    PaySerializer,
)
from .services import add_item, create_order, pay_order


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    # Catálogo público: qualquer visitante vê as marcas; só gestores as criam e alteram.
    permission_classes = [IsGestorOrReadOnly]


class CarViewSet(viewsets.ModelViewSet):
    queryset = Car.objects.select_related("brand")
    serializer_class = CarSerializer
    filterset_class = CarFilter
    search_fields = ["model", "version", "code", "brand__name"]
    ordering_fields = ["price", "year", "model", "created_at"]
    ordering = ["brand__name", "model", "version"]
    # Leitura pública (catálogo); criar, alterar e apagar só para gestores.
    permission_classes = [IsGestorOrReadOnly]


class OrderItemViewSet(viewsets.ModelViewSet):
    # O router usa este atributo para dar nome às rotas; os dados vêm de get_queryset.
    queryset = OrderItem.objects.select_related("car__brand")
    serializer_class = OrderItemSerializer
    filterset_fields = ["order"]
    ordering = ["id"]
    permission_classes = [IsAuthenticated, IsItemOwnerOrGestor]

    def get_queryset(self):
        qs = OrderItem.objects.select_related("car__brand", "order__customer")
        if is_gestor(self.request.user):
            return qs  # gestores veem todas as linhas
        # Um cliente só vê linhas das suas encomendas; as outras dão 404.
        return qs.filter(order__customer__user_id=self.request.user.id)

    def perform_create(self, serializer):
        # O serializer já confirmou que a encomenda é do utilizador (validate_order).
        data = serializer.validated_data
        serializer.instance = add_item(data["order"], data["car"], data["quantity"])


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
        items = OrderItem.objects.select_related("car__brand").order_by("id")
        line = F("items__quantity") * F("items__unit_price")
        return qs.prefetch_related(Prefetch("items", queryset=items)).annotate(total=Sum(line))

    def perform_create(self, serializer):
        # O dono vem sempre do utilizador autenticado, nunca do JSON enviado.
        # get_or_create: um utilizador sem perfil de cliente (ex.: um gestor) ganha um.
        customer, _ = Customer.objects.get_or_create(user=self.request.user)
        order = create_order(customer, serializer.validated_data["items"])
        # Relê com o total calculado e as linhas, para a resposta 201.
        serializer.instance = self.get_queryset().get(pk=order.pk)

    @extend_schema(
        request=PaySerializer,
        responses={
            200: OrderSerializer,
            409: OpenApiResponse(description="A encomenda já não está pendente ou não tem linhas."),
        },
    )
    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        # get_object() aplica o filtro do get_queryset (404 se não for tua)
        # e corre o IsOwnerOrGestor.has_object_permission.
        order = self.get_object()
        body = PaySerializer(data=request.data)
        body.is_valid(raise_exception=True)
        pay_order(order, body.validated_data["method"])
        order = self.get_queryset().get(pk=pk)  # relê com o total calculado
        return Response(self.get_serializer(order).data)
