"""Mudanças de estado da entrega, com a linha bloqueada (como o pay_order)."""

from django.db import transaction
from django.utils import timezone

from shop.models import Order
from shop.services import Conflict

from .models import Delivery


@transaction.atomic
def ship_delivery(delivery):
    """Agendada → em trânsito."""
    delivery = Delivery.objects.select_for_update().get(pk=delivery.pk)
    if delivery.status != Delivery.Status.SCHEDULED:
        raise Conflict(f"A entrega está '{delivery.get_status_display()}': já saiu do stand.")
    delivery.status = Delivery.Status.IN_TRANSIT
    delivery.save(update_fields=["status"])
    return delivery


@transaction.atomic
def complete_delivery(delivery):
    """Agendada ou em trânsito → entregue, e a encomenda passa a 'entregue'."""
    delivery = Delivery.objects.select_for_update().get(pk=delivery.pk)
    if delivery.status == Delivery.Status.DELIVERED:
        raise Conflict("A entrega já foi concluída.")
    order = Order.objects.select_for_update().get(pk=delivery.order_id)
    if order.status != Order.Status.PAID:
        raise Conflict(f"A encomenda está '{order.get_status_display()}' e não pode ser entregue.")
    delivery.status = Delivery.Status.DELIVERED
    delivery.delivered_at = timezone.now()
    delivery.save(update_fields=["status", "delivered_at"])
    order.status = Order.Status.DELIVERED
    order.save(update_fields=["status"])
    return delivery
