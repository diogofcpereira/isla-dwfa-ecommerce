# shop/tests/test_seed.py
"""O comando seed cria os dados de demonstração e pode correr várias vezes."""

import pytest
from django.contrib.auth import authenticate
from django.core.management import call_command

from shop.management.commands.seed import DEMO_CUSTOMERS, DEMO_GESTOR, DEMO_PASSWORD
from shop.models import Car, Customer, Order, Payment
from shop.permissions import is_gestor

pytestmark = pytest.mark.django_db


def test_seed_creates_demo_accounts_and_orders_in_every_state():
    call_command("seed", customers=5, orders=20, stdout=None)

    gestor = authenticate(username=DEMO_GESTOR, password=DEMO_PASSWORD)
    assert gestor is not None and is_gestor(gestor)
    for username in DEMO_CUSTOMERS:
        user = authenticate(username=username, password=DEMO_PASSWORD)
        assert user is not None and not is_gestor(user)
        states = set(user.customer.orders.values_list("status", flat=True))
        assert states == {"pending", "paid", "delivered", "cancelled"}

    assert Car.objects.count() == 20
    # Cada encomenda paga ou entregue tem o seu pagamento, com o total certo.
    assert Payment.objects.count() == Order.objects.filter(status__in=["paid", "delivered"]).count()
    assert not Car.objects.filter(stock__lt=0).exists()


def test_seed_twice_does_not_duplicate():
    call_command("seed", customers=5, orders=20, stdout=None)
    counts = (Car.objects.count(), Customer.objects.count(), Order.objects.count())
    call_command("seed", customers=5, orders=20, stdout=None)
    assert (Car.objects.count(), Customer.objects.count(), Order.objects.count()) == counts
