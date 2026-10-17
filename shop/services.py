from django.db import transaction
from django.db.models import Count

from .models import Category, OrderItem, Product


class OutOfStock(Exception):
    pass


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