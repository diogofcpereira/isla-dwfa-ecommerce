# testdrives/tests/test_test_drives.py
"""Recurso TestDrive: o cliente marca, o gestor confirma ou recusa, um horário por viatura."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from shop.factories import CarFactory, CustomerFactory
from shop.services import Conflict
from testdrives import models, services

pytestmark = pytest.mark.django_db
URL = "/api/v1/test-drives/"


def as_(user):
    api = APIClient()
    if user:
        api.force_authenticate(user=user)
    return api


def slot(days=2, hour=10):
    """Um horário certo (hh:00) daqui a `days` dias."""
    day = timezone.localtime() + timedelta(days=days)
    return day.replace(hour=hour, minute=0, second=0, microsecond=0)


def booking(customer, car=None, status="requested", **kwargs):
    return models.TestDrive.objects.create(
        customer=customer, car=car or CarFactory(), scheduled_for=slot(), status=status, **kwargs
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
def test_list_test_drives_by_role(actors, role, expected_status, expected_count):
    booking(actors["customer"].customer)  # a do cliente
    booking(CustomerFactory())  # a de outro cliente
    r = as_(actors[role]).get(URL)
    assert r.status_code == expected_status
    if expected_count is not None:
        assert r.json()["count"] == expected_count


def test_customer_books_a_test_drive(actors):
    car = CarFactory()
    body = {"car": car.id, "scheduled_for": slot().isoformat(), "notes": "De manhã, se possível."}
    r = as_(actors["customer"]).post(URL, body, format="json")
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "requested"
    assert data["customer"] == actors["customer"].customer.id


@pytest.mark.parametrize(
    "when,field",
    [
        (lambda: slot(days=-1), "scheduled_for"),  # no passado
        (lambda: slot() + timedelta(minutes=30), "scheduled_for"),  # não é hora certa
    ],
)
def test_booking_needs_a_future_slot_on_the_hour(actors, when, field):
    body = {"car": CarFactory().id, "scheduled_for": when().isoformat()}
    r = as_(actors["customer"]).post(URL, body, format="json")
    assert r.status_code == 400
    assert field in r.json()["errors"]


def test_inactive_car_cannot_be_booked(actors):
    body = {"car": CarFactory(is_active=False).id, "scheduled_for": slot().isoformat()}
    r = as_(actors["customer"]).post(URL, body, format="json")
    assert r.status_code == 400
    assert "car" in r.json()["errors"]


def test_a_slot_is_free_again_after_a_cancellation(actors):
    car = CarFactory()
    taken = booking(CustomerFactory(), car=car)
    body = {"car": car.id, "scheduled_for": slot().isoformat()}
    api = as_(actors["customer"])
    assert api.post(URL, body, format="json").status_code == 400  # horário ocupado

    taken.status = "cancelled"
    taken.save()
    assert api.post(URL, body, format="json").status_code == 201


def test_double_booking_in_a_race_is_a_409_not_a_500():
    # Dois pedidos ao mesmo tempo passam os dois no serializer; a constraint apanha o segundo.
    car = CarFactory()
    services.book_test_drive(CustomerFactory(), car, slot())
    with pytest.raises(Conflict):
        services.book_test_drive(CustomerFactory(), car, slot())
    assert models.TestDrive.objects.filter(car=car).count() == 1


@pytest.mark.parametrize("role,expected", [("anon", 401), ("customer", 403), ("gestor", 200)])
def test_confirm_by_role(actors, role, expected):
    mine = booking(actors["customer"].customer)
    r = as_(actors[role]).post(f"{URL}{mine.id}/confirm/")
    assert r.status_code == expected
    mine.refresh_from_db()
    assert mine.status == ("confirmed" if expected == 200 else "requested")


def test_state_changes_follow_the_rules(actors):
    gestor = as_(actors["gestor"])
    cancelled = booking(CustomerFactory(), status="cancelled")
    assert gestor.post(f"{URL}{cancelled.id}/confirm/").status_code == 409
    declined = booking(CustomerFactory())
    assert gestor.post(f"{URL}{declined.id}/decline/").json()["status"] == "declined"
    assert gestor.post(f"{URL}{declined.id}/decline/").status_code == 409


def test_customer_cancels_own_but_not_someone_elses(actors):
    api = as_(actors["customer"])
    mine = booking(actors["customer"].customer, status="confirmed")
    other = booking(CustomerFactory())
    assert api.post(f"{URL}{mine.id}/cancel/").json()["status"] == "cancelled"
    assert api.post(f"{URL}{mine.id}/cancel/").status_code == 409  # já cancelado
    assert api.post(f"{URL}{other.id}/cancel/").status_code == 404


def test_test_drive_list_has_no_n_plus_one(actors, django_assert_max_num_queries):
    customer = CustomerFactory()
    for _ in range(25):
        booking(customer)
    with django_assert_max_num_queries(3):  # grupos + count + marcações com viatura e marca
        r = as_(actors["gestor"]).get(URL)
    assert r.status_code == 200 and len(r.json()["results"]) == 20
