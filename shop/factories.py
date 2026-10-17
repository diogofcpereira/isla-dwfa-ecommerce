import uuid

import factory
from factory.django import DjangoModelFactory

from accounts.factories import UserFactory
from .models import Category, Customer, Order, OrderItem, Payment, Product


def short_id():
    return uuid.uuid4().hex[:8]


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.LazyFunction(lambda: f"Categoria {short_id()}")
    slug = factory.LazyAttribute(lambda o: o.name.lower().replace(" ", "-"))


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    category = factory.SubFactory(CategoryFactory)
    sku = factory.LazyFunction(lambda: f"SKU-{short_id().upper()}")
    name = factory.Faker("word")
    price = factory.Faker("pydecimal", left_digits=3, right_digits=2,
                          min_value=1, max_value=500)
    stock = factory.Faker("random_int", min=0, max=100)


class CustomerFactory(DjangoModelFactory):
    class Meta:
        model = Customer

    user = factory.SubFactory(UserFactory)


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    customer = factory.SubFactory(CustomerFactory)


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = factory.Faker("random_int", min=1, max=5)
    unit_price = factory.SelfAttribute("product.price")


class PaymentFactory(DjangoModelFactory):
    class Meta:
        model = Payment

    order = factory.SubFactory(OrderFactory)
    method = Payment.Method.CARD
    amount = factory.Faker("pydecimal", left_digits=3, right_digits=2,
                           min_value=1, max_value=500)