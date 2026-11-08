from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from shop.models import Customer
from shop.permissions import IsGestor, is_gestor

from . import services
from .models import TestDrive
from .permissions import IsTestDriveOwnerOrGestor
from .serializers import TestDriveSerializer

STATE_CHANGE = {
    200: TestDriveSerializer,
    409: OpenApiResponse(description="O estado atual do test drive não o permite."),
}


class TestDriveViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Marcações de test drive.

    - cliente: marca (POST), vê as suas e cancela-as (POST /{id}/cancel/);
    - gestor: vê todas, confirma e recusa (POST /{id}/confirm/ e /{id}/decline/).
    Não há PUT/PATCH nem DELETE: muda-se de horário cancelando e marcando de novo.
    """

    queryset = TestDrive.objects.select_related("car__brand", "customer")
    serializer_class = TestDriveSerializer
    filterset_fields = ["status", "car"]
    ordering_fields = ["scheduled_for", "created_at"]
    ordering = ["scheduled_for"]
    permission_classes = [IsAuthenticated, IsTestDriveOwnerOrGestor]

    def get_queryset(self):
        qs = TestDrive.objects.select_related("car__brand", "customer")
        if is_gestor(self.request.user):
            return qs
        return qs.filter(customer__user_id=self.request.user.id)  # os outros dão 404

    def perform_create(self, serializer):
        customer, _ = Customer.objects.get_or_create(user=self.request.user)
        data = serializer.validated_data
        serializer.instance = services.book_test_drive(
            customer, data["car"], data["scheduled_for"], data.get("notes", "")
        )

    @extend_schema(request=None, responses=STATE_CHANGE)
    @action(detail=True, methods=["post"], permission_classes=[IsGestor])
    def confirm(self, request, pk=None):
        return Response(self.get_serializer(services.confirm(self.get_object())).data)

    @extend_schema(request=None, responses=STATE_CHANGE)
    @action(detail=True, methods=["post"], permission_classes=[IsGestor])
    def decline(self, request, pk=None):
        return Response(self.get_serializer(services.decline(self.get_object())).data)

    @extend_schema(request=None, responses=STATE_CHANGE)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        # get_object(): filtro do get_queryset (404 se não for tua) + IsTestDriveOwnerOrGestor.
        return Response(self.get_serializer(services.cancel(self.get_object())).data)
