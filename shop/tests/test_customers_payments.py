# shop/tests/test_customers_payments.py
"""Perfis de cliente e pagamentos: cada um vê o seu, o gestor vê tudo."""

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from shop.factories import CustomerFactory, OrderFactory, PaymentFactory

pytestmark = pytest.mark.django_db


def as_(user):
    api = APIClient()
    api.force_authenticate(user=user)
    return api


@pytest.fixture
def gestor():
    user = UserFactory()
    user.groups.add(Group.objects.get(name="gestores"))
    return user


def test_customer_sees_and_edits_only_own_profile():
    me = CustomerFactory()
    other = CustomerFactory()
    api = as_(me.user)

    listed = api.get("/api/v1/customers/").json()["results"]
    assert [c["id"] for c in listed] == [me.id]

    r = api.patch(f"/api/v1/customers/{me.id}/", {"phone": "912345678"}, format="json")
    assert r.status_code == 200
    me.refresh_from_db()
    assert me.phone == "912345678"

    assert api.get(f"/api/v1/customers/{other.id}/").status_code == 404


def test_profile_cannot_be_moved_to_another_user():
    me = CustomerFactory()
    stranger = UserFactory()
    r = as_(me.user).patch(f"/api/v1/customers/{me.id}/", {"user": stranger.id}, format="json")
    assert r.status_code == 200
    me.refresh_from_db()
    assert me.user_id != stranger.id  # o campo user é só de leitura


def test_profiles_are_not_created_or_deleted_through_the_api(gestor):
    customer = CustomerFactory()
    api = as_(gestor)
    assert api.post("/api/v1/customers/", {}, format="json").status_code == 405
    assert api.delete(f"/api/v1/customers/{customer.id}/").status_code == 405


def test_customer_only_sees_own_payments_and_gestor_sees_all(gestor):
    mine = PaymentFactory(order=OrderFactory(status="paid"))
    PaymentFactory(order=OrderFactory(status="paid"))  # de outro cliente
    owner = mine.order.customer.user

    listed = as_(owner).get("/api/v1/payments/").json()["results"]
    assert [p["id"] for p in listed] == [mine.id]
    assert as_(gestor).get("/api/v1/payments/").json()["count"] == 2


def test_payments_are_read_only(gestor):
    order = OrderFactory()
    body = {"order": order.id, "method": "card", "amount": "100.00"}
    assert as_(gestor).post("/api/v1/payments/", body, format="json").status_code == 405
