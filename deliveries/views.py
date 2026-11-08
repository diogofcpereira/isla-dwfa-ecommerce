from django.db import IntegrityError, transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from shop.permissions import IsGestorOrReadOnly, is_gestor
from shop.services import Conflict

from .models import Delivery
from .permissions import IsDeliveryOwnerOrGestor
from .serializers import DeliverySerializer
from .services import complete_delivery, ship_delivery

STATE_CHANGE = {
    200: DeliverySerializer,
    409: OpenApiResponse(description="O estado da entrega ou da encomenda não o permite."),
}


class DeliveryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Entregas. O gestor agenda, altera e conclui; o cliente acompanha as suas.

    Não há DELETE: uma entrega fica no histórico da encomenda.
    """

    queryset = Delivery.objects.select_related("order__customer")
    serializer_class = DeliverySerializer
    filterset_fields = ["status", "order"]
    search_fields = ["address"]
    ordering_fields = ["scheduled_for", "created_at"]
    ordering = ["scheduled_for"]
    # IsAuthenticated: anónimo → 401. IsGestorOrReadOnly: cliente só lê → 403 ao escrever.
    permission_classes = [IsAuthenticated, IsGestorOrReadOnly, IsDeliveryOwnerOrGestor]

    def get_queryset(self):
        qs = Delivery.objects.select_related("order__customer")
        if is_gestor(self.request.user):
            return qs
        # O cliente só vê as entregas das suas encomendas; as outras dão 404.
        return qs.filter(order__customer__user_id=self.request.user.id)

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            # Dois pedidos ao mesmo tempo para a mesma encomenda: a OneToOne apanha o segundo.
            raise ValidationError({"order": "Esta encomenda já tem uma entrega."}) from None

    def perform_update(self, serializer):
        # Uma entrega concluída é um registo do que aconteceu: a data e a morada já não mudam.
        if serializer.instance.status == Delivery.Status.DELIVERED:
            raise Conflict("A entrega já foi concluída e não pode ser alterada.")
        serializer.save()

    @extend_schema(request=None, responses=STATE_CHANGE)
    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        delivery = ship_delivery(self.get_object())
        return Response(self.get_serializer(delivery).data)

    @extend_schema(request=None, responses=STATE_CHANGE)
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        delivery = complete_delivery(self.get_object())
        return Response(self.get_serializer(delivery).data)
