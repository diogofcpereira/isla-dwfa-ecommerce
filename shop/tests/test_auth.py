import pytest
from rest_framework.test import APIClient

from accounts.factories import UserFactory


@pytest.mark.django_db
def test_orders_require_auth():
    r = APIClient().get("/api/v1/orders/")
    assert r.status_code == 401


@pytest.mark.django_db
def test_login_returns_pair():
    UserFactory(username="ana", password="pass1234")
    r = APIClient().post(
        "/api/v1/auth/token/",
        {"username": "ana", "password": "pass1234"},
        format="json",
    )
    assert r.status_code == 200
    assert {"access", "refresh"} <= r.json().keys()