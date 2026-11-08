# shop/tests/test_api.py
import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from shop.factories import CarFactory, CustomerFactory, OrderFactory, OrderItemFactory
from shop.models import OrderItem


@pytest.fixture
def api():
    """Cliente HTTP anónimo (sem login)."""
    return APIClient()


@pytest.fixture
def gestor_api(db):
    """Cliente autenticado como gestor: vê e altera todas as encomendas."""
    user = UserFactory()
    group, _ = Group.objects.get_or_create(name="gestores")
    user.groups.add(group)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_car_list_is_paginated(api):
    # Anónimo de propósito: prova que o catálogo é público.
    CarFactory.create_batch(25)
    response = api.get("/api/v1/cars/")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"count", "next", "previous", "results"}
    assert body["count"] == 25 and len(body["results"]) == 20


@pytest.mark.django_db
def test_create_item_and_reject_quantity_above_stock(gestor_api):
    order = OrderFactory()
    car = CarFactory(stock=3)
    ok = gestor_api.post(
        "/api/v1/order-items/",
        {"order": order.pk, "car": car.pk, "quantity": 2},
        format="json",
    )
    assert ok.status_code == 201
    assert OrderItem.objects.filter(order=order, car=car).exists()

    scarce = CarFactory(stock=1)
    bad = gestor_api.post(
        "/api/v1/order-items/",
        {"order": order.pk, "car": scarce.pk, "quantity": 5},
        format="json",
    )
    assert bad.status_code == 400
    assert "quantity" in bad.json()["errors"]


@pytest.mark.django_db
def test_order_list_is_paginated_without_n_plus_one(gestor_api, django_assert_max_num_queries):
    for order in OrderFactory.create_batch(25):
        OrderItemFactory.create_batch(3, order=order)
    with django_assert_max_num_queries(4):  # grupos (is_gestor) + count + encomendas + linhas
        response = gestor_api.get("/api/v1/orders/")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 25 and len(body["results"]) == 20


@pytest.mark.django_db
def test_customer_cannot_add_item_to_someone_elses_order():
    other_order = OrderFactory()  # encomenda de outro cliente
    me = CustomerFactory().user  # eu: um cliente diferente
    client = APIClient()
    client.force_authenticate(user=me)
    r = client.post(
        "/api/v1/order-items/",
        {"order": other_order.pk, "car": CarFactory(stock=5).pk, "quantity": 1},
        format="json",
    )
    assert r.status_code == 400
    assert "order" in r.json()["errors"]  # o erro aponta para o campo order
    assert not OrderItem.objects.filter(order=other_order).exists()


@pytest.mark.django_db
def test_inactive_car_cannot_be_ordered(gestor_api):
    order = OrderFactory()
    car = CarFactory(stock=5, is_active=False)
    r = gestor_api.post(
        "/api/v1/order-items/",
        {"order": order.pk, "car": car.pk, "quantity": 1},
        format="json",
    )
    assert r.status_code == 400
    assert "car" in r.json()["errors"]
    assert not OrderItem.objects.filter(order=order).exists()


@pytest.mark.django_db
def test_car_year_out_of_range_is_rejected(gestor_api):
    body = {
        "brand": CarFactory().brand_id,
        "code": "DN-ANO-1",
        "model": "Clio",
        "year": 1985,
        "fuel": "diesel",
        "price": "22800.00",
        "stock": 1,
    }
    r = gestor_api.post("/api/v1/cars/", body, format="json")
    assert r.status_code == 400
    assert "year" in r.json()["errors"]


@pytest.mark.django_db
def test_car_list_filters_by_fuel_and_max_price(api):
    CarFactory(fuel="electric", price="39900.00")
    CarFactory(fuel="electric", price="52990.00")
    CarFactory(fuel="diesel", price="22800.00")
    r = api.get("/api/v1/cars/", {"fuel": "electric", "max_price": "45000"})
    assert r.status_code == 200
    assert [c["price"] for c in r.json()["results"]] == ["39900.00"]
