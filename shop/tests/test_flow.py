# shop/tests/test_flow.py
"""Fluxo de negócio do M1: encomendar viaturas (com linhas) e pagar."""

import pytest
from rest_framework.test import APIClient

from shop.factories import CarFactory, CustomerFactory, OrderFactory, OrderItemFactory
from shop.models import Order, OrderItem, Payment
from shop.services import OutOfStock, add_item, create_order

pytestmark = pytest.mark.django_db


@pytest.fixture
def customer(db):
    return CustomerFactory()


@pytest.fixture
def api(customer):
    client = APIClient()
    client.force_authenticate(user=customer.user)
    return client


def test_order_is_created_with_its_lines_in_one_request(api, customer):
    golf = CarFactory(stock=3, price="32500.00")
    yaris = CarFactory(stock=2, price="23900.00")
    body = {"items": [{"car": golf.id, "quantity": 2}, {"car": yaris.id, "quantity": 1}]}

    r = api.post("/api/v1/orders/", body, format="json")

    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert len(data["items"]) == 2
    assert data["total"] == "88900.00"  # 2 × 32500 + 23900
    golf.refresh_from_db()
    yaris.refresh_from_db()
    assert (golf.stock, yaris.stock) == (1, 1)
    assert Order.objects.get().customer == customer


def test_an_invalid_line_leaves_nothing_created(api):
    ok = CarFactory(stock=5)
    retired = CarFactory(stock=5, is_active=False)
    body = {"items": [{"car": ok.id, "quantity": 1}, {"car": retired.id, "quantity": 1}]}

    r = api.post("/api/v1/orders/", body, format="json")

    assert r.status_code == 400
    assert not Order.objects.exists()
    ok.refresh_from_db()
    assert ok.stock == 5


def test_order_without_lines_or_with_repeated_car_is_rejected(api):
    car = CarFactory(stock=5)
    assert api.post("/api/v1/orders/", {"items": []}, format="json").status_code == 400
    twice = {"items": [{"car": car.id, "quantity": 1}, {"car": car.id, "quantity": 1}]}
    assert api.post("/api/v1/orders/", twice, format="json").status_code == 400
    assert not Order.objects.exists()


def test_create_order_rolls_back_when_stock_runs_out(customer):
    # Simula o caso concorrente: o serializer já validou, mas entretanto o stock acabou.
    first = CarFactory(stock=5)
    second = CarFactory(stock=1)
    lines = [{"car": first, "quantity": 2}, {"car": second, "quantity": 3}]

    with pytest.raises(OutOfStock):
        create_order(customer, lines)

    assert not Order.objects.exists() and not OrderItem.objects.exists()
    first.refresh_from_db()
    assert first.stock == 5  # a primeira linha também foi desfeita


def test_out_of_stock_is_a_409_not_a_500():
    car = CarFactory(stock=1)
    with pytest.raises(OutOfStock) as error:
        add_item(OrderFactory(), car, quantity=2)
    assert error.value.status_code == 409


def test_pay_creates_the_payment_and_a_second_pay_is_409(api, customer):
    order = OrderFactory(customer=customer)
    OrderItemFactory(order=order, quantity=2, unit_price="20000.00")

    first = api.post(f"/api/v1/orders/{order.id}/pay/", {"method": "financing"}, format="json")
    assert first.status_code == 200
    assert first.json()["status"] == "paid"
    payment = Payment.objects.get(order=order)
    assert (payment.method, str(payment.amount)) == ("financing", "40000.00")

    again = api.post(f"/api/v1/orders/{order.id}/pay/", {"method": "card"}, format="json")
    assert again.status_code == 409
    assert Payment.objects.filter(order=order).count() == 1


def test_pay_needs_a_valid_method_and_an_order_with_lines(api, customer):
    order = OrderFactory(customer=customer)
    OrderItemFactory(order=order)
    assert api.post(f"/api/v1/orders/{order.id}/pay/", {}, format="json").status_code == 400
    bad = {"method": "bitcoin"}
    assert api.post(f"/api/v1/orders/{order.id}/pay/", bad, format="json").status_code == 400

    empty = OrderFactory(customer=customer)
    r = api.post(f"/api/v1/orders/{empty.id}/pay/", {"method": "card"}, format="json")
    assert r.status_code == 409
    assert not Payment.objects.exists()