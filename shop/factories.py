import uuid

import factory
from factory.django import DjangoModelFactory

from accounts.factories import UserFactory

from .models import Brand, Car, Customer, Order, OrderItem, Payment


def short_id():
    return uuid.uuid4().hex[:8]


class BrandFactory(DjangoModelFactory):
    class Meta:
        model = Brand
        django_get_or_create = ("slug",)

    name = factory.LazyFunction(lambda: f"Marca {short_id()}")
    slug = factory.LazyAttribute(lambda o: o.name.lower().replace(" ", "-"))


class CarFactory(DjangoModelFactory):
    class Meta:
        model = Car
        django_get_or_create = ("code",)

    brand = factory.SubFactory(BrandFactory)
    code = factory.LazyFunction(lambda: f"DN-{short_id().upper()}")
    model = factory.Faker("word")
    version = "1.5 Base"
    year = factory.Faker("random_int", min=2019, max=2026)
    fuel = factory.Iterator([c for c, _ in Car.Fuel.choices])
    price = factory.Faker(
        "pydecimal", left_digits=5, right_digits=2, min_value=12000, max_value=90000
    )
    stock = factory.Faker("random_int", min=1, max=10)


class CustomerFactory(DjangoModelFactory):
    class Meta:
        model = Customer
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory)


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    customer = factory.SubFactory(CustomerFactory)


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    car = factory.SubFactory(CarFactory)
    quantity = factory.Faker("random_int", min=1, max=3)
    unit_price = factory.SelfAttribute("car.price")


class PaymentFactory(DjangoModelFactory):
    class Meta:
        model = Payment

    order = factory.SubFactory(OrderFactory)
    method = Payment.Method.TRANSFER
    amount = factory.Faker(
        "pydecimal", left_digits=5, right_digits=2, min_value=12000, max_value=90000
    )
