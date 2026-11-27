"""Filtros da lista de entregas (M2, extra do Diogo)."""

import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import Delivery


def overdue_q():
    """Em atraso: ainda não foi entregue e a data prevista já passou."""
    return Q(scheduled_for__lt=timezone.now()) & ~Q(status=Delivery.Status.DELIVERED)


class DeliveryFilter(django_filters.FilterSet):
    """?status=, ?order= (como no M1) e ?overdue=true (só as entregas em atraso)."""

    overdue = django_filters.BooleanFilter(
        method="filter_overdue",
        label="Em atraso: por entregar e com a data prevista já passada.",
    )

    class Meta:
        model = Delivery
        fields = ["status", "order"]

    def filter_overdue(self, queryset, name, value):
        return queryset.filter(overdue_q()) if value else queryset.exclude(overdue_q())
