# deliveries/tests/test_deliveries.py
"""Recurso Delivery: o gestor agenda e conclui entregas; o cliente acompanha as suas."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from deliveries.models import Delivery
from shop.factories import CustomerFactory, OrderFactory

pytestmark = pytest.mark.django_db


def as_(user):
    api = APIClient()
    if user:
        api.force_authenticate(user=user)
    return api


def tomorrow():
    return timezone.now() + timedelta(days=1)


def paid_order(**kwargs):
    return OrderFactory(status="paid", **kwargs)


def delivery_for(order, **kwargs):
    return Delivery.objects.create(
        order=order, scheduled_for=tomorrow(), address="Rua do Stand, 1", **kwargs
    )


@pytest.fixture
def actors():
    gestor = UserFactory()
    gestor.groups.add(Group.objects.get(name="gestores"))
    return {"anon": None, "customer": CustomerFactory().user, "gestor": gestor}


@pytest.mark.parametrize(
    "role,expected_status,expected_count",
    [("anon", 401, None), ("customer", 200, 1), ("gestor", 200, 2)],
)
def test_list_deliveries_by_role(actors, role, expected_status, expected_count):
    delivery_for(paid_order(customer=actors["customer"].customer))  # a do cliente
    delivery_for(paid_order())  # a de outro cliente
    r = as_(actors[role]).get("/api/v1/deliveries/")
    assert r.status_code == expected_status
    if expected_count is not None:
        assert r.json()["count"] == expected_count


@pytest.mark.parametrize("role,expected", [("anon", 401), ("customer", 403), ("gestor", 201)])
def test_create_delivery_by_role(actors, role, expected):
    order = paid_order(customer=actors["customer"].customer)
    body = {"order": order.id, "scheduled_for": tomorrow().isoformat(), "address": "Rua A, 10"}
    r = as_(actors[role]).post("/api/v1/deliveries/", body, format="json")
    assert r.status_code == expected
    if expected == 201:
        assert r.json()["status"] == "scheduled"


def test_only_paid_orders_get_a_delivery_and_only_one(actors):
    api = as_(actors["gestor"])
    pending = OrderFactory()  # pendente: ainda não foi paga
    body = {"order": pending.id, "scheduled_for": tomorrow().isoformat(), "address": "Rua A"}
    r = api.post("/api/v1/deliveries/", body, format="json")
    assert r.status_code == 400
    assert "order" in r.json()["errors"]

    order = paid_order()
    delivery_for(order)
    body["order"] = order.id
    again = api.post("/api/v1/deliveries/", body, format="json")
    assert again.status_code == 400  # OneToOne: já tem entrega


def test_delivery_date_must_be_in_the_future(actors):
    body = {
        "order": paid_order().id,
        "scheduled_for": (timezone.now() - timedelta(hours=1)).isoformat(),
        "address": "Rua A",
    }
    r = as_(actors["gestor"]).post("/api/v1/deliveries/", body, format="json")
    assert r.status_code == 400
    assert "scheduled_for" in r.json()["errors"]


def test_complete_marks_the_order_as_delivered_and_twice_is_409(actors):
    order = paid_order()
    delivery = delivery_for(order)
    api = as_(actors["gestor"])

    assert api.post(f"/api/v1/deliveries/{delivery.id}/ship/").json()["status"] == "in_transit"
    done = api.post(f"/api/v1/deliveries/{delivery.id}/complete/")
    assert done.status_code == 200
    assert done.json()["status"] == "delivered" and done.json()["delivered_at"]
    order.refresh_from_db()
    assert order.status == "delivered"

    assert api.post(f"/api/v1/deliveries/{delivery.id}/complete/").status_code == 409
    assert api.post(f"/api/v1/deliveries/{delivery.id}/ship/").status_code == 409


@pytest.mark.parametrize("role,expected", [("anon", 401), ("customer", 404), ("gestor", 200)])
def test_other_customers_delivery_by_role(actors, role, expected):
    other = delivery_for(paid_order())
    r = as_(actors[role]).get(f"/api/v1/deliveries/{other.id}/")
    assert r.status_code == expected


def test_customer_cannot_complete_own_delivery(actors):
    mine = delivery_for(paid_order(customer=actors["customer"].customer))
    r = as_(actors["customer"]).post(f"/api/v1/deliveries/{mine.id}/complete/")
    assert r.status_code == 403
    mine.refresh_from_db()
    assert mine.status == "scheduled"


def test_delivery_list_has_no_n_plus_one(actors, django_assert_max_num_queries):
    for order in OrderFactory.create_batch(25, status="paid"):
        delivery_for(order)
    with django_assert_max_num_queries(3):  # grupos + count + entregas com a encomenda
        r = as_(actors["gestor"]).get("/api/v1/deliveries/")
    assert r.status_code == 200 and len(r.json()["results"]) == 20