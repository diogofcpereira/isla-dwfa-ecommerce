# reviews/tests/test_reviews.py
"""Recurso Review: só avalia quem comprou; o gestor modera; o público vê as aprovadas."""

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from reviews.models import Review
from shop.factories import CarFactory, CustomerFactory, OrderFactory, OrderItemFactory

pytestmark = pytest.mark.django_db


def as_(user):
    api = APIClient()
    if user:
        api.force_authenticate(user=user)
    return api


def buyer_of(car, status="paid"):
    """Um cliente com uma encomenda (paga, por omissão) desta viatura."""
    customer = CustomerFactory()
    OrderItemFactory(order=OrderFactory(customer=customer, status=status), car=car)
    return customer


def review(car, customer, status="pending", rating=4):
    return Review.objects.create(car=car, customer=customer, rating=rating, status=status)


@pytest.fixture
def gestor():
    user = UserFactory()
    user.groups.add(Group.objects.get(name="gestores"))
    return user


def test_public_list_only_shows_approved_reviews():
    car = CarFactory()
    approved = review(car, buyer_of(car), status="approved")
    review(car, buyer_of(car), status="pending")
    review(car, buyer_of(car), status="hidden")
    r = APIClient().get("/api/v1/reviews/")
    assert r.status_code == 200
    assert [x["id"] for x in r.json()["results"]] == [approved.id]


def test_customer_sees_approved_reviews_and_own_pending_one():
    car = CarFactory()
    approved = review(car, buyer_of(car), status="approved")
    me = buyer_of(car)
    mine = review(car, me)  # pendente
    ids = {x["id"] for x in as_(me.user).get("/api/v1/reviews/").json()["results"]}
    assert ids == {approved.id, mine.id}


def test_buyer_can_review_and_review_starts_pending():
    car = CarFactory()
    me = buyer_of(car, status="delivered")
    body = {"car": car.id, "rating": 5, "comment": "Excelente compra."}
    r = as_(me.user).post("/api/v1/reviews/", body, format="json")
    assert r.status_code == 201
    assert r.json()["status"] == "pending" and r.json()["customer"] == me.id


@pytest.mark.parametrize("order_status", [None, "pending", "cancelled"])
def test_only_who_bought_the_car_can_review_it(order_status):
    car = CarFactory()
    me = buyer_of(car, status=order_status) if order_status else CustomerFactory()
    r = as_(me.user).post("/api/v1/reviews/", {"car": car.id, "rating": 3}, format="json")
    assert r.status_code == 400
    assert "car" in r.json()["errors"]
    assert not Review.objects.exists()


def test_second_review_of_the_same_car_is_rejected():
    car = CarFactory()
    me = buyer_of(car)
    review(car, me)
    r = as_(me.user).post("/api/v1/reviews/", {"car": car.id, "rating": 2}, format="json")
    assert r.status_code == 400
    assert Review.objects.count() == 1


def test_rating_must_be_between_1_and_5():
    car = CarFactory()
    me = buyer_of(car)
    r = as_(me.user).post("/api/v1/reviews/", {"car": car.id, "rating": 6}, format="json")
    assert r.status_code == 400
    assert "rating" in r.json()["errors"]


@pytest.mark.parametrize("role,expected", [("anon", 401), ("customer", 403), ("gestor", 200)])
def test_moderate_by_role(gestor, role, expected):
    car = CarFactory()
    author = buyer_of(car)
    target = review(car, author)
    users = {"anon": None, "customer": author.user, "gestor": gestor}
    r = as_(users[role]).post(
        f"/api/v1/reviews/{target.id}/moderate/", {"status": "approved"}, format="json"
    )
    assert r.status_code == expected
    target.refresh_from_db()
    assert target.status == ("approved" if expected == 200 else "pending")


def test_editing_a_review_sends_it_back_to_moderation():
    car = CarFactory()
    me = buyer_of(car)
    mine = review(car, me, status="approved")
    r = as_(me.user).patch(f"/api/v1/reviews/{mine.id}/", {"rating": 2}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "pending" and r.json()["rating"] == 2


def test_customer_cannot_edit_or_delete_someone_elses_review():
    car = CarFactory()
    public = review(car, buyer_of(car), status="approved")  # visível, mas não é dele
    hidden = review(car, buyer_of(car), status="pending")  # nem sequer a vê
    me = buyer_of(car).user
    patch = as_(me).patch(f"/api/v1/reviews/{public.id}/", {"rating": 1}, format="json")
    assert patch.status_code == 403
    assert as_(me).delete(f"/api/v1/reviews/{public.id}/").status_code == 403
    assert as_(me).delete(f"/api/v1/reviews/{hidden.id}/").status_code == 404


def test_review_list_has_no_n_plus_one(django_assert_max_num_queries):
    car = CarFactory()
    for _ in range(25):
        review(car, buyer_of(car), status="approved")
    with django_assert_max_num_queries(3):  # count + avaliações com viatura, marca e autor
        r = APIClient().get("/api/v1/reviews/")
    assert r.status_code == 200 and len(r.json()["results"]) == 20
