import random

import factory
from django.core.management.base import BaseCommand
from django.db import transaction

from shop.factories import (CategoryFactory, CustomerFactory,
                            OrderFactory, OrderItemFactory, ProductFactory)
from shop.models import Category, Customer, Order, Product


class Command(BaseCommand):
    help = "Preenche a BD com dados de exemplo. Pode correr várias vezes."

    def add_arguments(self, parser):
        parser.add_argument("--categories", type=int, default=8)
        parser.add_argument("--products", type=int, default=120)
        parser.add_argument("--customers", type=int, default=40)
        parser.add_argument("--orders", type=int, default=150)

    @transaction.atomic
    def handle(self, *args, **opts):
        # Idempotente: só cria o que falta para chegar aos totais pedidos.
        missing = opts["categories"] - Category.objects.count()
        CategoryFactory.create_batch(max(missing, 0))
        categories = list(Category.objects.all())

        missing = opts["products"] - Product.objects.count()
        ProductFactory.create_batch(
            max(missing, 0), category=factory.Iterator(categories))
        products = list(Product.objects.all())

        missing = opts["customers"] - Customer.objects.count()
        CustomerFactory.create_batch(max(missing, 0))
        customers = list(Customer.objects.all())

        missing = opts["orders"] - Order.objects.count()
        for _ in range(max(missing, 0)):
            order = OrderFactory(customer=random.choice(customers))
            for product in random.sample(products, k=random.randint(1, 4)):
                OrderItemFactory(order=order, product=product)

        self.stdout.write(self.style.SUCCESS(
            f"{Category.objects.count()} categorias, "
            f"{Product.objects.count()} produtos, "
            f"{Order.objects.count()} encomendas."))