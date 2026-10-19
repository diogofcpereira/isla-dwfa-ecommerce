from django.db import transaction
from django.db.models import Count
from rest_framework.exceptions import APIException

from .models import Category, Order, OrderItem, Product


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
        order=order, product=product,
        quantity=quantity, unit_price=product.price)
    product.stock -= quantity
    product.save(update_fields=["stock"])
    return item

@transaction.atomic
def pay_order(order):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != Order.Status.PENDING:
        raise Conflict(f"A encomenda está '{order.get_status_display()}' e não pode ser paga.")
    order.status = Order.Status.PAID
    order.save(update_fields=["status"])
    return order