# deliveries/tests/test_notifications.py
"""M2 (extra do Diogo): o cliente recebe um email quando a entrega é agendada, sai e chega.

Os testes do pytest-django correm dentro de uma transação que nunca faz commit, por isso
os on_commit só correm dentro do django_capture_on_commit_callbacks(execute=True).
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth.models import Group
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from deliveries.models import Delivery
from shop.factories import CustomerFactory, OrderFactory

pytestmark = pytest.mark.django_db

LISBON = ZoneInfo("Europe/Lisbon")


@pytest.fixture
def gestor_api():
    gestor = UserFactory()
    gestor.groups.add(Group.objects.get(name="gestores"))
    api = APIClient()
    api.force_authenticate(user=gestor)
    return api


@pytest.fixture
def order():
    """Uma encomenda paga da Ana, que tem email."""
    user = UserFactory(username="ana", email="ana@example.com", first_name="Ana")
    return OrderFactory(status="paid", customer=CustomerFactory(user=user))


def schedule(api, order, when):
    body = {"order": order.id, "scheduled_for": when.isoformat(), "address": "Rua das Flores, 10"}
    return api.post("/api/v1/deliveries/", body, format="json")


def test_scheduling_emails_the_date_and_the_address(
    gestor_api, order, django_capture_on_commit_callbacks
):
    when = (
        (timezone.now() + timedelta(days=3))
        .astimezone(LISBON)
        .replace(hour=10, minute=30, second=0, microsecond=0)
    )
    with django_capture_on_commit_callbacks(execute=True):
        r = schedule(gestor_api, order, when)
    assert r.status_code == 201

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == ["ana@example.com"]
    assert email.from_email == "DriveNow <entregas@drivenow.example>"
    assert email.subject == f"A entrega da encomenda #{order.id} foi agendada"
    assert email.body.startswith("Olá Ana,")
    assert f"{when:%d/%m/%Y} às 10:30" in email.body  # na hora de Lisboa
    assert "Rua das Flores, 10" in email.body


def test_ship_and_complete_each_send_one_email(
    gestor_api, order, django_capture_on_commit_callbacks
):
    delivery = Delivery.objects.create(
        order=order, scheduled_for=timezone.now() + timedelta(days=1), address="Rua A, 1"
    )
    with django_capture_on_commit_callbacks(execute=True):
        assert gestor_api.post(f"/api/v1/deliveries/{delivery.id}/ship/").status_code == 200
        assert gestor_api.post(f"/api/v1/deliveries/{delivery.id}/complete/").status_code == 200

    assert [m.subject for m in mail.outbox] == [
        f"A encomenda #{order.id} saiu do stand",
        f"A encomenda #{order.id} foi entregue",
    ]
    assert "Já pode avaliar a viatura" in mail.outbox[1].body


def test_a_refused_request_sends_nothing(gestor_api, order, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        past = schedule(gestor_api, order, timezone.now() - timedelta(hours=1))  # 400
        delivery = Delivery.objects.create(
            order=order, scheduled_for=timezone.now() + timedelta(days=1), address="Rua A, 1"
        )
        Delivery.objects.filter(pk=delivery.pk).update(
            status="delivered", delivered_at=timezone.now()
        )
        again = gestor_api.post(f"/api/v1/deliveries/{delivery.id}/complete/")  # 409
    assert (past.status_code, again.status_code) == (400, 409)
    assert mail.outbox == []


def test_no_email_until_the_change_is_committed(gestor_api, order):
    # Sem o capture, o on_commit fica à espera do commit que o teste nunca faz:
    # é a prova de que o email não sai a meio da transação.
    r = schedule(gestor_api, order, timezone.now() + timedelta(days=1))
    assert r.status_code == 201
    assert mail.outbox == []


def test_a_mail_server_failure_does_not_break_the_api(
    gestor_api, order, django_capture_on_commit_callbacks, monkeypatch, caplog
):
    def broken(*args, **kwargs):
        raise ConnectionRefusedError("SMTP em baixo")

    monkeypatch.setattr("deliveries.notifications.send_mail", broken)
    with django_capture_on_commit_callbacks(execute=True):
        r = schedule(gestor_api, order, timezone.now() + timedelta(days=1))
    assert r.status_code == 201  # a entrega fica agendada na mesma
    assert Delivery.objects.filter(order=order).exists()
    assert "não enviado" in caplog.text


def test_a_customer_without_email_is_skipped(gestor_api, django_capture_on_commit_callbacks):
    no_email = CustomerFactory(user=UserFactory(email=""))
    order = OrderFactory(status="paid", customer=no_email)
    with django_capture_on_commit_callbacks(execute=True):
        r = schedule(gestor_api, order, timezone.now() + timedelta(days=1))
    assert r.status_code == 201
    assert mail.outbox == []


def test_when_uses_lisbon_time():
    from deliveries.notifications import when

    utc = datetime(2026, 7, 1, 9, 30, tzinfo=ZoneInfo("UTC"))  # verão: Lisboa = UTC+1
    assert when(utc) == "01/07/2026 às 10:30"
