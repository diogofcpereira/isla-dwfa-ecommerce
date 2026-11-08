# shop/tests/test_stock.py
"""O stock acompanha as alterações às encomendas, e uma encomenda paga já não muda."""

import pytest
from rest_framework.test import APIClient

from shop.factories import CarFactory, CustomerFactory, OrderFactory
from shop.models import Order, OrderItem
from shop.services import add_item

pytestmark = pytest.mark.django_db


@pytest.fixture
def customer():
    return CustomerFactory()


@pytest.fixture
def api(customer):
    client = APIClient()
    client.force_authenticate(user=customer.user)
    return client


@pytest.fixture
def line(customer):
    """Uma linha de 2 unidades numa encomenda pendente; ficam 3 em stock."""
    car = CarFactory(stock=5)
    return add_item(OrderFactory(customer=customer), car, quantity=2)


def stock_of(item):
    item.car.refresh_from_db()
    return item.car.stock


def test_changing_quantity_adjusts_stock(api, line):
    r = api.patch(f"/api/v1/order-items/{line.id}/", {"quantity": 4}, format="json")
    assert r.status_code == 200
    assert stock_of(line) == 1  # 5 - 4

    r = api.patch(f"/api/v1/order-items/{line.id}/", {"quantity": 1}, format="json")
    assert r.status_code == 200
    assert stock_of(line) == 4  # devolveu 3


def test_changing_quantity_above_stock_is_rejected(api, line):
    r = api.patch(f"/api/v1/order-items/{line.id}/", {"quantity": 9}, format="json")
    assert r.status_code == 409
    line.refresh_from_db()
    assert line.quantity == 2 and stock_of(line) == 3


def test_car_of_an_existing_line_cannot_change(api, line):
    other = CarFactory(stock=5)
    r = api.patch(f"/api/v1/order-items/{line.id}/", {"car": other.id}, format="json")
    assert r.status_code == 400


def test_deleting_a_line_or_an_order_returns_the_stock(api, customer, line):
    assert api.delete(f"/api/v1/order-items/{line.id}/").status_code == 204
    assert stock_of(line) == 5

    car = CarFactory(stock=2)
    item = add_item(OrderFactory(customer=customer), car, quantity=2)
    assert api.delete(f"/api/v1/orders/{item.order_id}/").status_code == 204
    car.refresh_from_db()
    assert car.stock == 2
    assert not Order.objects.filter(pk=item.order_id).exists()


def test_paid_order_cannot_be_deleted_or_changed(api, line):
    pay = api.post(f"/api/v1/orders/{line.order_id}/pay/", {"method": "card"}, format="json")
    assert pay.status_code == 200

    assert api.delete(f"/api/v1/orders/{line.order_id}/").status_code == 409
    assert api.delete(f"/api/v1/order-items/{line.id}/").status_code == 409
    patch = api.patch(f"/api/v1/order-items/{line.id}/", {"quantity": 1}, format="json")
    assert patch.status_code == 409
    new_line = {"order": line.order_id, "car": CarFactory(stock=5).id, "quantity": 1}
    assert api.post("/api/v1/order-items/", new_line, format="json").status_code == 409
    assert OrderItem.objects.filter(order_id=line.order_id).count() == 1
    assert stock_of(line) == 3
