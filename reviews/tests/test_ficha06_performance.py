# reviews/tests/test_ficha06_performance.py
"""Ficha 06 (Filipe): a lista de avaliações faz as mesmas queries com 5 ou com 20 avaliações.

O tempo mede-se fora dos testes, com volume (scripts/measure.py e docs/ficha-06.md); aqui
conta-se o número de queries, que não depende do relógio nem do runner do CI. Se alguém
tirar o select_related("car__brand", "customer__user") da view, o campo `car_name` do
serializer (source="car.name", que usa a marca) passa a fazer queries por avaliação e este
teste falha.
"""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from reviews.models import Review
from shop.factories import CarFactory, CustomerFactory

pytestmark = pytest.mark.django_db

URL = reverse("review-list")


@pytest.fixture
def gestor_api():
    gestor = UserFactory()
    gestor.groups.add(Group.objects.get(name="gestores"))
    api = APIClient()
    api.force_authenticate(user=gestor)
    return api


def make_reviews(n):
    """`n` avaliações, cada uma de uma viatura e de um cliente diferentes."""
    for i in range(n):
        Review.objects.create(
            car=CarFactory(), customer=CustomerFactory(), rating=1 + i % 5, status="approved"
        )


def test_review_list_query_count_does_not_grow(gestor_api, django_assert_num_queries):
    make_reviews(5)
    gestor_api.get(URL)  # aquece (o primeiro pedido paga o que estiver frio)
    # 1 é gestor? (auth_group) · 1 COUNT da paginação · 1 avaliações com viatura, marca e
    # cliente (JOIN)
    with django_assert_num_queries(3):
        assert gestor_api.get(URL).status_code == 200
    make_reviews(15)
    with django_assert_num_queries(3):
        body = gestor_api.get(URL).json()
    assert body["count"] == 20 and len(body["results"]) == 20
    # A ordem que o índice ix_review_created_desc serve: a mais recente primeiro.
    dates = [r["created_at"] for r in body["results"]]
    assert dates == sorted(dates, reverse=True)
