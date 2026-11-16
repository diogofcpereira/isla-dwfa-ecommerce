from django.db import transaction
from django.db.models import Count, F, Sum
from rest_framework.exceptions import APIException

from .models import Category, Order, OrderItem, Payment, Product
from .tasks import send_order_receipt


class OutOfStock(Exception):
    pass


class Conflict(APIException):
    status_code = 409
    default_detail = "O estado atual não permite esta operação."
    default_code = "conflict"


def categories_with_counts():
    return Category.objects.annotate(n=Count("products")).order_by("name")


@transaction.atomic
def add_item(order, product, quantity):
    # bloqueia a linha do produto até ao fim da transação
    product = Product.objects.select_for_update().get(pk=product.pk)
    if quantity > product.stock:
        raise OutOfStock(f"Só há {product.stock} em stock.")
    item = OrderItem.objects.create(
        order=order, product=product, quantity=quantity, unit_price=product.price
    )
    product.stock -= quantity
    product.save(update_fields=["stock"])
    return item


@transaction.atomic
def pay_order(order):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != Order.Status.PENDING:
        raise Conflict(f"A encomenda está '{order.get_status_display()}' e não pode ser paga.")
    # O total é calculado aqui, no servidor, em Decimal (nunca vem do cliente).
    total = order.items.aggregate(total=Sum(F("quantity") * F("unit_price")))["total"]
    if not total:
        raise Conflict("Uma encomenda sem linhas não pode ser paga.")
    order.status = Order.Status.PAID
    order.save(update_fields=["status"])
    # Ficha 05: o pagamento fica registado (é aí que vive o receipt_sent_at do recibo).
    # Simulado: não há gateway a sério; o método por omissão é cartão.
    Payment.objects.create(
        order=order,
        method=Payment.Method.CARD,
        amount=total,
        gateway_response={"simulated": True},
    )

    # Ficha 05: o recibo sai numa tarefa Celery, e só DEPOIS do commit. Um .delay() aqui
    # dentro podia chegar ao worker antes do commit (Payment.DoesNotExist), ou mandar o
    # recibo de um pagamento que a seguir fazia rollback.
    transaction.on_commit(lambda: send_order_receipt.delay(order.pk))
    return order
