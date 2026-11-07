from django.db import transaction
from django.db.models import Count, F, Sum
from rest_framework.exceptions import APIException

from .models import Brand, Car, Order, OrderItem, Payment


class Conflict(APIException):
    status_code = 409
    default_detail = "O estado atual não permite esta operação."
    default_code = "conflict"


class OutOfStock(Conflict):
    """Stock insuficiente no momento de gravar (ex.: dois clientes ao mesmo tempo).

    É um Conflict, por isso a API responde 409 em vez de rebentar com um 500.
    """

    default_detail = "Não há stock suficiente desta viatura."
    default_code = "out_of_stock"


def brands_with_counts():
    """Marcas com o número de viaturas de cada uma, numa só query."""
    return Brand.objects.annotate(n=Count("cars")).order_by("name")


def order_total(order):
    """Soma das linhas (quantidade × preço unitário) de uma encomenda."""
    line = F("quantity") * F("unit_price")
    return order.items.aggregate(total=Sum(line))["total"] or 0


@transaction.atomic
def add_item(order, car, quantity):
    # Bloqueia a linha da viatura até ao fim da transação: dois clientes não
    # conseguem comprar a última unidade ao mesmo tempo.
    car = Car.objects.select_for_update().get(pk=car.pk)
    if quantity > car.stock:
        raise OutOfStock(f"Só há {car.stock} em stock de {car.name}.")
    item = OrderItem.objects.create(order=order, car=car, quantity=quantity, unit_price=car.price)
    car.stock -= quantity
    car.save(update_fields=["stock"])
    return item


@transaction.atomic
def create_order(customer, lines):
    """Cria a encomenda e todas as linhas numa só transação.

    `lines` é uma lista de dicionários {"car": Car, "quantity": int}. Se uma linha
    falhar (ex.: sem stock), a exceção desfaz tudo: nem a encomenda nem as linhas
    anteriores ficam gravadas, e o stock das outras viaturas volta ao que era.
    """
    order = Order.objects.create(customer=customer)
    # Ordenar pelo id evita deadlocks: duas encomendas bloqueiam as viaturas pela mesma ordem.
    for line in sorted(lines, key=lambda line: line["car"].pk):
        add_item(order, line["car"], line["quantity"])
    return order


@transaction.atomic
def pay_order(order, method):
    """Pendente → paga, e regista o Payment com o total da encomenda."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != Order.Status.PENDING:
        raise Conflict(f"A encomenda está '{order.get_status_display()}' e não pode ser paga.")
    total = order_total(order)
    if total <= 0:
        raise Conflict("A encomenda não tem linhas: não há nada para pagar.")
    Payment.objects.create(order=order, method=method, amount=total)
    order.status = Order.Status.PAID
    order.save(update_fields=["status"])
    return order