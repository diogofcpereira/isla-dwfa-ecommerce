# shop/tests/test_tasks.py
"""Ficha 05: tarefas Celery, em modo eager (sem Redis): config/settings/test.py.

Os testes provam as regras, não o código: o recibo sai uma vez, só depois do commit,
e o estado de uma tarefa só se mostra ao dono.
"""

import pytest
from django.core import mail
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from shop.factories import CustomerFactory, OrderFactory, OrderItemFactory, PaymentFactory
from shop.models import Payment
from shop.tasks import send_order_receipt


def as_(user):
    api = APIClient()
    api.force_authenticate(user=user)
    return api


# ---------- Parte 1: o recibo ----------


@pytest.mark.django_db
def test_receipt_is_idempotent():
    payment = PaymentFactory()

    first = send_order_receipt.delay(payment.order_id)
    again = send_order_receipt.delay(payment.order_id)  # o broker entregou duas vezes

    assert first.get() == "sent"
    assert again.get() == "already-sent"
    assert len(mail.outbox) == 1  # um só email
    assert mail.outbox[0].to == [payment.order.customer.user.email]
    payment.refresh_from_db()
    assert payment.receipt_sent_at is not None


@pytest.mark.django_db
def test_pay_enqueues_receipt_only_after_commit(django_capture_on_commit_callbacks):
    order = OrderFactory()
    OrderItemFactory(order=order, quantity=2, unit_price="10.00")
    api = as_(order.customer.user)

    # execute=False: guarda os callbacks do on_commit sem os correr.
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        r = api.post(f"/api/v1/orders/{order.id}/pay/")

    assert r.status_code == 200 and r.json()["status"] == "paid"
    assert len(callbacks) == 1  # o recibo foi enfileirado no commit…
    assert len(mail.outbox) == 0  # …e nada saiu antes dele
    assert Payment.objects.get(order=order).amount == 20  # o total da API, em Decimal

    callbacks[0]()  # "o commit aconteceu": agora a tarefa corre
    assert len(mail.outbox) == 1
    assert f"#{order.id}" in mail.outbox[0].subject


@pytest.mark.django_db
def test_empty_order_cannot_be_paid():
    order = OrderFactory()  # sem linhas: o Payment teria amount 0 (a constraint proíbe)
    r = as_(order.customer.user).post(f"/api/v1/orders/{order.id}/pay/")
    assert r.status_code == 409


# ---------- Parte 2: 202 e o estado só para o dono ----------


@pytest.mark.django_db
def test_report_is_accepted_and_only_the_owner_sees_it():
    ana = UserFactory(username="ana")
    cliente = CustomerFactory(user=ana)
    for _ in range(3):
        OrderItemFactory(order__customer=cliente, quantity=1, unit_price="5.00")
    OrderItemFactory()  # uma encomenda de outro cliente: não pode contar

    r = as_(ana).post("/api/v1/reports/orders/")

    assert r.status_code == 202
    status_url = r.json()["status_url"]
    assert status_url == f"/api/v1/tasks/{r.json()['id']}/"
    assert r["Location"] == status_url

    s = as_(ana).get(status_url)  # eager: a tarefa já acabou
    assert s.status_code == 200
    body = s.json()
    assert body["state"] == "SUCCESS"
    assert body["result"] == {"orders": 3, "amount": "15.00", "by_status": {"pending": 3}}

    bruno = UserFactory(username="bruno")
    assert as_(bruno).get(status_url).status_code == 404  # alheia → 404
    assert as_(ana).get("/api/v1/tasks/nao-existe/").status_code == 404  # desconhecida → 404
    assert APIClient().get(status_url).status_code == 401  # anónimo → 401
