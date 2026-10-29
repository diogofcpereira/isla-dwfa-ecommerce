# shop/tests/test_auth.py
"""Testes de autenticação e autorização (Ficha 03).

Cada teste verifica uma ou mais linhas da matriz endpoint × papel do docs/decisions.md.
401 = quem és? · 403 = podes? · 404 = existe para ti?
"""
import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from shop.factories import (CategoryFactory, CustomerFactory, OrderFactory,
                            OrderItemFactory, ProductFactory)
from shop.models import Order

# ---------- Auxiliares ----------


@pytest.fixture
def actors(db):
    """Os três papéis da matriz. O grupo 'gestores' vem da migração 0002."""
    gestor = UserFactory()
    gestor.groups.add(Group.objects.get(name="gestores"))
    return {"anon": None, "customer": UserFactory(), "gestor": gestor}


def as_(user):
    """Cliente HTTP autenticado como `user` (ou anónimo se None), sem passar pelo JWT."""
    api = APIClient()
    if user:
        api.force_authenticate(user=user)
    return api


def items(response):
    """Lista de resultados de uma resposta paginada."""
    return response.json()["results"]


# ---------- Parte 1: JWT ----------


@pytest.mark.django_db
def test_orders_require_auth():
    r = APIClient().get("/api/v1/orders/")
    assert r.status_code == 401


@pytest.mark.django_db
def test_login_returns_pair():
    UserFactory(username="ana", password="pass1234")
    r = APIClient().post("/api/v1/auth/token/",
                         {"username": "ana", "password": "pass1234"}, format="json")
    assert r.status_code == 200
    assert {"access", "refresh"} <= r.json().keys()


@pytest.mark.django_db
def test_refresh_token_cannot_be_reused():
    UserFactory(username="ana", password="pass1234")
    api = APIClient()
    pair = api.post("/api/v1/auth/token/",
                    {"username": "ana", "password": "pass1234"}, format="json").json()

    first = api.post("/api/v1/auth/token/refresh/",
                     {"refresh": pair["refresh"]}, format="json")
    assert first.status_code == 200
    assert first.json()["refresh"] != pair["refresh"]      # rotação: refresh novo

    again = api.post("/api/v1/auth/token/refresh/",
                     {"refresh": pair["refresh"]}, format="json")
    assert again.status_code == 401                        # o antigo está na blacklist
    assert again.json()["code"] == "token_not_valid"


@pytest.mark.parametrize("role,expected", [("anon", 401), ("customer", 200), ("gestor", 200)])
def test_me_by_role(actors, role, expected):
    r = as_(actors[role]).get("/api/v1/me/")
    assert r.status_code == expected
    if role == "gestor":
        assert r.json()["groups"] == ["gestores"]


# ---------- Parte 2: produtos por papel ----------


@pytest.mark.django_db
def test_anonymous_can_read_catalog():
    ProductFactory()
    assert APIClient().get("/api/v1/products/").status_code == 200
    assert APIClient().get("/api/v1/categories/").status_code == 200


@pytest.mark.parametrize("role,expected", [("anon", 401), ("customer", 403), ("gestor", 201)])
def test_create_product_by_role(actors, role, expected):
    body = {"category": CategoryFactory().id, "sku": "SKU-TESTE-1", "name": "Lamp",
            "price": "9.90", "stock": 3}
    r = as_(actors[role]).post("/api/v1/products/", body, format="json")
    assert r.status_code == expected


@pytest.mark.parametrize("role,expected", [("anon", 401), ("customer", 403), ("gestor", 200)])
def test_patch_product_by_role(actors, role, expected):
    product = ProductFactory()
    r = as_(actors[role]).patch(f"/api/v1/products/{product.id}/", {"stock": 10}, format="json")
    assert r.status_code == expected


# ---------- Parte 2: encomendas por papel e por objeto ----------


@pytest.mark.parametrize("role,expected_status,expected_count", [
    ("anon", 401, None),
    ("customer", 200, 1),   # só a sua
    ("gestor", 200, 2),     # todas
])
def test_list_orders_by_role(actors, role, expected_status, expected_count):
    OrderFactory(customer__user=actors["customer"])   # a encomenda do cliente
    OrderFactory()                                    # a de outra pessoa
    r = as_(actors[role]).get("/api/v1/orders/")
    assert r.status_code == expected_status
    if expected_count is not None:
        assert len(items(r)) == expected_count


@pytest.mark.parametrize("method,suffix", [("get", ""), ("post", "pay/")])
def test_other_customers_order_is_404(actors, method, suffix):
    other = OrderFactory()                            # de outro cliente
    r = getattr(as_(actors["customer"]), method)(f"/api/v1/orders/{other.id}/{suffix}")
    assert r.status_code == 404


def test_customer_can_pay_own_order(actors):
    order = OrderFactory(customer__user=actors["customer"])
    OrderItemFactory(order=order)
    r = as_(actors["customer"]).post(f"/api/v1/orders/{order.id}/pay/")
    assert r.status_code == 200
    assert r.json()["status"] == "paid"


def test_new_order_belongs_to_whoever_is_logged_in(actors):
    stranger = CustomerFactory()                      # tenta pôr a encomenda em nome dele
    r = as_(actors["customer"]).post("/api/v1/orders/",
                                     {"customer": stranger.id}, format="json")
    assert r.status_code == 201
    order = Order.objects.get(pk=r.json()["id"])
    assert order.customer.user == actors["customer"]  # o campo enviado foi ignorado


def test_owner_cannot_change_status(actors):
    order = OrderFactory(customer__user=actors["customer"])
    before = order.status
    r = as_(actors["customer"]).patch(f"/api/v1/orders/{order.id}/",
                                      {"status": "paid"}, format="json")
    assert r.status_code == 200                       # o pedido é aceite...
    order.refresh_from_db()
    assert order.status == before                     # ...mas o status não mudou


# ---------- Parte 2: linhas de encomenda ----------


def test_customer_only_sees_items_of_own_orders(actors):
    mine = OrderItemFactory(order__customer__user=actors["customer"])
    OrderItemFactory()                                # linha de outra encomenda
    r = as_(actors["customer"]).get("/api/v1/order-items/")
    assert r.status_code == 200
    assert [i["id"] for i in items(r)] == [mine.id]