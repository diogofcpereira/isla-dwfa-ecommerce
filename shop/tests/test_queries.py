# shop/tests/test_queries.py
"""Nenhum endpoint de lista tem N+1: o número de queries não cresce com os dados.

Cada teste cria 25 objetos (mais do que uma página de 20) e mede as queries de
uma página. Sem os select_related/prefetch_related das views, estes números
passavam de 3–4 para 20 ou mais.
"""

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from shop.factories import (
    BrandFactory,
    CarFactory,
    CustomerFactory,
    OrderFactory,
    OrderItemFactory,
    PaymentFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def gestor_api():
    user = UserFactory()
    user.groups.add(Group.objects.get(name="gestores"))
    api = APIClient()
    api.force_authenticate(user=user)
    return api


def test_car_list_takes_at_most_3_queries(django_assert_max_num_queries):
    for brand in BrandFactory.create_batch(5):
        CarFactory.create_batch(5, brand=brand)
    with django_assert_max_num_queries(3):  # count + viaturas com a marca (JOIN)
        r = APIClient().get("/api/v1/cars/")
    assert r.status_code == 200 and len(r.json()["results"]) == 20


def test_brand_list_takes_at_most_3_queries(django_assert_max_num_queries):
    BrandFactory.create_batch(25)
    with django_assert_max_num_queries(3):  # count + marcas
        r = APIClient().get("/api/v1/brands/")
    assert r.status_code == 200 and len(r.json()["results"]) == 20


# Nas listas autenticadas há mais 1 query: a do is_gestor() (grupos do utilizador).


def test_order_item_list_has_no_n_plus_one(gestor_api, django_assert_max_num_queries):
    OrderItemFactory.create_batch(25)
    with django_assert_max_num_queries(3):  # grupos + count + linhas com viatura e marca
        r = gestor_api.get("/api/v1/order-items/")
    assert r.status_code == 200 and len(r.json()["results"]) == 20


def test_customer_list_has_no_n_plus_one(gestor_api, django_assert_max_num_queries):
    CustomerFactory.create_batch(25)
    with django_assert_max_num_queries(3):  # grupos + count + clientes com utilizador
        r = gestor_api.get("/api/v1/customers/")
    assert r.status_code == 200 and len(r.json()["results"]) == 20


def test_payment_list_has_no_n_plus_one(gestor_api, django_assert_max_num_queries):
    PaymentFactory.create_batch(25)
    with django_assert_max_num_queries(3):  # grupos + count + pagamentos
        r = gestor_api.get("/api/v1/payments/")
    assert r.status_code == 200 and len(r.json()["results"]) == 20


def test_customer_order_list_has_no_n_plus_one(django_assert_max_num_queries):
    customer = CustomerFactory()
    for order in OrderFactory.create_batch(25, customer=customer):
        OrderItemFactory.create_batch(2, order=order)
    api = APIClient()
    api.force_authenticate(user=customer.user)
    with django_assert_max_num_queries(4):  # grupos + count + encomendas + linhas
        r = api.get("/api/v1/orders/")
    assert r.status_code == 200 and len(r.json()["results"]) == 20
