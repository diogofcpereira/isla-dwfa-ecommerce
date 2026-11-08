"""Regras de negócio do DriveNow.

As views só recebem o pedido e devolvem a resposta; o que mexe em stock,
estados e pagamentos vive aqui, dentro de transações.
"""

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


def ensure_pending(order):
    """Só uma encomenda pendente pode mudar de linhas ou ser apagada."""
    if order.status != Order.Status.PENDING:
        raise Conflict(
            f"A encomenda está '{order.get_status_display()}': as linhas já não podem mudar."
        )


@transaction.atomic
def add_item(order, car, quantity):
    order = Order.objects.select_for_update().get(pk=order.pk)
    ensure_pending(order)
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
def change_quantity(item, quantity):
    """Muda a quantidade de uma linha e acerta o stock pela diferença."""
    item = OrderItem.objects.select_for_update().select_related("order").get(pk=item.pk)
    ensure_pending(item.order)
    car = Car.objects.select_for_update().get(pk=item.car_id)
    delta = quantity - item.quantity  # > 0: tira do stock; < 0: devolve
    if delta > car.stock:
        raise OutOfStock(f"Só há mais {car.stock} em stock de {car.name}.")
    car.stock -= delta
    car.save(update_fields=["stock"])
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    return item


@transaction.atomic
def remove_item(item):
    """Apaga uma linha e devolve as unidades ao stock."""
    item = OrderItem.objects.select_for_update().select_related("order").get(pk=item.pk)
    ensure_pending(item.order)
    Car.objects.filter(pk=item.car_id).update(stock=F("stock") + item.quantity)
    item.delete()


@transaction.atomic
def delete_order(order):
    """Apaga uma encomenda pendente e devolve ao stock as unidades de todas as linhas.

    Uma encomenda paga ou entregue não se apaga (tem um Payment, que a protege).
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    ensure_pending(order)
    for item in order.items.all():
        Car.objects.filter(pk=item.car_id).update(stock=F("stock") + item.quantity)
    order.delete()


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
