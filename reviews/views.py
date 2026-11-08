"""Views do recurso Review."""

from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from shop.models import Customer
from shop.permissions import IsGestor, is_gestor

from .models import Review
from .permissions import IsReviewAuthorOrGestor
from .serializers import ModerationSerializer, ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    """Avaliações de viaturas.

    - anónimos: veem as aprovadas;
    - cliente: vê as aprovadas e as suas; cria, edita e apaga as suas;
    - gestor: vê todas e modera (POST /reviews/{id}/moderate/).
    """

    queryset = Review.objects.select_related("car__brand", "customer__user")
    serializer_class = ReviewSerializer
    filterset_fields = ["car", "rating", "status"]
    search_fields = ["comment"]
    ordering_fields = ["created_at", "rating"]
    ordering = ["-created_at"]
    permission_classes = [IsAuthenticatedOrReadOnly, IsReviewAuthorOrGestor]

    def get_queryset(self):
        qs = Review.objects.select_related("car__brand", "customer__user")
        user = self.request.user
        if is_gestor(user):
            return qs
        visible = Q(status=Review.Status.APPROVED)
        if user.is_authenticated:
            visible |= Q(customer__user_id=user.id)  # as suas, mesmo por aprovar
        return qs.filter(visible)

    def perform_create(self, serializer):
        customer, _ = Customer.objects.get_or_create(user=self.request.user)
        serializer.save(customer=customer)

    def perform_update(self, serializer):
        # Uma avaliação editada volta a precisar de moderação.
        serializer.save(status=Review.Status.PENDING)

    @extend_schema(request=ModerationSerializer, responses=ReviewSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsGestor])
    def moderate(self, request, pk=None):
        review = self.get_object()
        body = ModerationSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        review.status = body.validated_data["status"]
        review.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(review).data)
