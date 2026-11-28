# shop/tests/test_seed_big.py
"""Ficha 06: o comando seed_big cria volume, com os estados desiguais, e não corre duas vezes."""

import pytest
from django.core.management import CommandError, call_command

from deliveries.models import Delivery
from reviews.models import Review
from shop.models import Order, OrderItem, Payment
from testdrives import models as testdrives

pytestmark = pytest.mark.django_db

SMALL = {"customers": 10, "orders": 100, "reviews": 50, "test_drives": 40}


def test_seed_big_needs_the_demo_catalogue():
    with pytest.raises(CommandError, match="seed"):
        call_command("seed_big", **SMALL, stdout=None)


def test_seed_big_creates_volume_with_uneven_states():
    call_command("seed", customers=2, orders=8, stdout=None)
    before = Order.objects.count()
    call_command("seed_big", **SMALL, stdout=None)

    assert Order.objects.count() == before + 100
    big = Order.objects.filter(customer__user__username__startswith="big-")
    assert big.filter(status="pending").count() == 10  # 1 em cada 10
    assert big.filter(status="delivered").count() == 40
    assert OrderItem.objects.filter(order__in=big).count() == 134  # 2 linhas em 1 de cada 3
    # Um pagamento por encomenda paga ou entregue, e uma entrega por cada entregue.
    paid = big.filter(status__in=["paid", "delivered"])
    assert Payment.objects.filter(order__in=big).count() == paid.count()
    assert Delivery.objects.filter(order__in=big, status="delivered").count() == 40
    assert Review.objects.filter(customer__user__username__startswith="big-").count() == 50
    assert (
        testdrives.TestDrive.objects.filter(customer__user__username__startswith="big-").count()
        == 40
    )

    call_command("seed_big", **SMALL, stdout=None)  # segunda vez: não duplica
    assert Order.objects.count() == before + 100
