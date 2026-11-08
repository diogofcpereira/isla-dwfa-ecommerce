# core/tests/test_errors.py
"""Os erros da API seguem a RFC 9457 (Problem Details)."""

import pytest
from rest_framework.test import APIClient

from shop.factories import CustomerFactory, OrderFactory

pytestmark = pytest.mark.django_db

PROBLEM = "application/problem+json"


def test_401_is_a_problem_document():
    r = APIClient().get("/api/v1/orders/")
    assert r.status_code == 401
    assert r["Content-Type"] == PROBLEM
    body = r.json()
    assert body["type"] == "about:blank"
    assert body["title"] == "Unauthorized"
    assert body["status"] == 401
    assert body["instance"] == "/api/v1/orders/"
    assert body["detail"]


def test_404_on_someone_elses_order_is_a_problem_document():
    api = APIClient()
    api.force_authenticate(user=CustomerFactory().user)
    r = api.get(f"/api/v1/orders/{OrderFactory().id}/")
    assert r.status_code == 404
    assert r.json()["title"] == "Not Found"


def test_validation_errors_go_in_errors_by_field():
    api = APIClient()
    api.force_authenticate(user=CustomerFactory().user)
    r = api.post("/api/v1/orders/", {"items": []}, format="json")
    assert r.status_code == 400
    assert r["Content-Type"] == PROBLEM
    body = r.json()
    assert body["title"] == "Bad Request"
    assert "items" in body["errors"]


def test_409_keeps_the_error_code():
    api = APIClient()
    customer = CustomerFactory()
    api.force_authenticate(user=customer.user)
    empty = OrderFactory(customer=customer)  # sem linhas: não se pode pagar
    r = api.post(f"/api/v1/orders/{empty.id}/pay/", {"method": "card"}, format="json")
    assert r.status_code == 409
    assert r.json()["code"] == "conflict"
