# testdrives/tests/test_ficha06_performance.py
"""Ficha 06 (Rúben): a agenda de test drives faz as mesmas queries com 5 ou com 20 marcações.

O tempo mede-se fora dos testes, com volume (scripts/measure.py e docs/ficha-06.md); aqui
conta-se o número de queries, que não depende do relógio nem do runner do CI. Se alguém
tirar o select_related("car__brand", "customer__user") da view, o campo `car_name` do
serializer (source="car.name", que usa a marca) passa a fazer queries por marcação e este
teste falha.
"""

from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from shop.factories import CarFactory, CustomerFactory
from testdrives import models

pytestmark = pytest.mark.django_db

URL = reverse("testdrive-list")


@pytest.fixture
def gestor_api():
    gestor = UserFactory()
    gestor.groups.add(Group.objects.get(name="gestores"))
    api = APIClient()
    api.force_authenticate(user=gestor)
    return api


def make_test_drives(n):
    """`n` marcações, cada uma de uma viatura e de um cliente diferentes, à hora certa."""
    start = (timezone.now() + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
    for i in range(n):
        models.TestDrive.objects.create(
            car=CarFactory(),
            customer=CustomerFactory(),
            scheduled_for=start + timedelta(hours=i),
        )


def test_test_drive_list_query_count_does_not_grow(gestor_api, django_assert_num_queries):
    make_test_drives(5)
    gestor_api.get(URL)  # aquece (o primeiro pedido paga o que estiver frio)
    # 1 é gestor? (auth_group) · 1 COUNT da paginação · 1 marcações com viatura, marca e
    # cliente (JOIN)
    with django_assert_num_queries(3):
        assert gestor_api.get(URL).status_code == 200
    make_test_drives(15)
    with django_assert_num_queries(3):
        body = gestor_api.get(URL).json()
    assert body["count"] == 20 and len(body["results"]) == 20
    # A ordem que o índice ix_testdrive_scheduled_for serve: a mais próxima primeiro.
    dates = [t["scheduled_for"] for t in body["results"]]
    assert dates == sorted(dates)
