from django.db import transaction
from django.db.models import Count
from rest_framework.exceptions import APIException

from .models import Brand, Car, Order, OrderItem


class OutOfStock(Exception):
    pass


class Conflict(APIException):
    status_code = 409
    default_detail = "O estado atual não permite esta operação."
    default_code = "conflict"


def brands_with_counts():
    """Marcas com o número de viaturas de cada uma, numa só query."""
    return Brand.objects.annotate(n=Count("cars")).order_by("name")


@transaction.atomic
def add_item(order, car, quantity):
    # Bloqueia a linha da viatura até ao fim da transação: dois clientes não
    # conseguem comprar a última unidade ao mesmo tempo.
    car = Car.objects.select_for_update().get(pk=car.pk)
    if quantity > car.stock:
        raise OutOfStock(f"Só há {car.stock} em stock.")
    item = OrderItem.objects.create(order=order, car=car, quantity=quantity, unit_price=car.price)
    car.stock -= quantity
    car.save(update_fields=["stock"])
    return item


@transaction.atomic
def pay_order(order):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != Order.Status.PENDING:
        raise Conflict(f"A encomenda está '{order.get_status_display()}' e não pode ser paga.")
    order.status = Order.Status.PAID
    order.save(update_fields=["status"])
    return order
