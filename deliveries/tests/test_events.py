# deliveries/tests/test_events.py
"""Ficha 06 · Parte 3 (opção B): os eventos das entregas saem no log, depois do commit."""

import json
import logging
from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from core.logs import JsonFormatter
from deliveries.models import Delivery
from shop.factories import OrderFactory

pytestmark = pytest.mark.django_db


def test_delivery_events_are_logged_after_commit_with_ids_only(
    caplog, django_capture_on_commit_callbacks
):
    caplog.set_level(logging.INFO, logger="drivenow.deliveries")
    gestor = UserFactory()
    gestor.groups.add(Group.objects.get(name="gestores"))
    api = APIClient()
    api.force_authenticate(user=gestor)
    order = OrderFactory(status="paid")
    when = (timezone.now() + timedelta(days=2)).isoformat()

    with django_capture_on_commit_callbacks(execute=True):
        r = api.post(
            "/api/v1/deliveries/",
            {"order": order.pk, "scheduled_for": when, "address": "Rua Secreta, 7"},
            format="json",
        )
    assert r.status_code == 201
    delivery = Delivery.objects.get(order=order)
    with django_capture_on_commit_callbacks(execute=True):
        api.post(f"/api/v1/deliveries/{delivery.pk}/ship/")
    with django_capture_on_commit_callbacks(execute=True):
        api.post(f"/api/v1/deliveries/{delivery.pk}/complete/")

    events = [rec for rec in caplog.records if rec.name == "drivenow.deliveries"]
    assert [e.getMessage() for e in events] == [
        "delivery_scheduled",
        "delivery_shipped",
        "delivery_completed",
    ]
    line = json.loads(JsonFormatter().format(events[-1]))
    assert line["delivery_id"] == delivery.pk and line["order_id"] == order.pk
    assert line["status"] == "delivered" and line["user_id"] == gestor.pk
    # Ids só: a morada (e o email ou o nome do cliente) não vão para o log.
    assert "Rua Secreta" not in json.dumps(line)
