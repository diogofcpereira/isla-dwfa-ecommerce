# deliveries/tests/test_ficha06_performance.py
"""Ficha 06 (Diogo): a lista de entregas faz as mesmas queries com 5 ou com 20 entregas.

O tempo mede-se fora dos testes, com volume (scripts/measure.py e docs/ficha-06.md); aqui
conta-se o número de queries, que não depende do relógio nem do runner do CI. Se alguém
tirar o select_related("order__customer") da view, o campo `customer` do serializer
(source="order.customer_id") passa a fazer uma query por entrega e este teste falha.
"""

from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from deliveries.models import Delivery
from shop.factories import OrderFactory

pytestmark = pytest.mark.django_db

URL = reverse("delivery-list")


@pytest.fixture
def gestor_api():
    gestor = UserFactory()
    gestor.groups.add(Group.objects.get(name="gestores"))
    api = APIClient()
    api.force_authenticate(user=gestor)
    return api


def make_deliveries(n):
    """`n` entregas de encomendas pagas, cada uma de um cliente diferente."""
    for i in range(n):
        Delivery.objects.create(
            order=OrderFactory(status="paid"),
            scheduled_for=timezone.now() + timedelta(days=1 + i),
            address=f"Rua do Stand, {i}",
        )


def test_delivery_list_query_count_does_not_grow(gestor_api, django_assert_num_queries):
    make_deliveries(5)
    gestor_api.get(URL)  # aquece (o primeiro pedido paga o que estiver frio)
    # 1 é gestor? (auth_group) · 1 COUNT da paginação · 1 entregas com a encomenda (JOIN)
    with django_assert_num_queries(3):
        assert gestor_api.get(URL).status_code == 200
    make_deliveries(15)
    with django_assert_num_queries(3):
        body = gestor_api.get(URL).json()
    assert body["count"] == 20 and len(body["results"]) == 20
    # A ordem que o índice ix_delivery_scheduled_for serve: a mais próxima primeiro.
    dates = [d["scheduled_for"] for d in body["results"]]
    assert dates == sorted(dates)
