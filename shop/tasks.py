"""Tarefas Celery da loja (Ficha 05).

Três regras: ids, nunca objetos (a mensagem é JSON e a linha pode ter mudado);
idempotentes (o broker entrega pelo menos uma vez); enfileiradas depois do commit.
"""

import time
from decimal import Decimal
from smtplib import SMTPException

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from .models import Order, Payment


class ReceiptGatewayError(Exception):
    """Falha transitória ao enviar o recibo (o servidor de email não respondeu)."""


@shared_task(
    bind=True,
    acks_late=True,  # se o worker morrer a meio, a mensagem volta para a fila
    # Só o que é transitório se repete. Um DoesNotExist falhava igual mais três vezes.
    autoretry_for=(ReceiptGatewayError, SMTPException, ConnectionError, TimeoutError),
    retry_backoff=2,  # 2 s, 4 s, 8 s…
    retry_backoff_max=60,
    retry_jitter=True,  # ± aleatório, para os workers não baterem à porta ao mesmo tempo
    max_retries=3,
)
def send_order_receipt(self, order_id: int) -> str:
    """Envia o recibo da encomenda `order_id`. Correr duas vezes = correr uma."""
    with transaction.atomic():
        # select_for_update: dois workers com a mesma mensagem não enviam os dois;
        # o segundo espera pelo commit do primeiro e depois vê o receipt_sent_at.
        payment = (
            Payment.objects.select_for_update()
            .select_related("order__customer__user")
            .get(order_id=order_id)
        )
        if payment.receipt_sent_at is not None:
            return "already-sent"

        # Para ver os retries no worker: RECEIPT_FLAKY=1 no .env faz a 1.ª tentativa falhar.
        if getattr(settings, "RECEIPT_FLAKY", False) and self.request.retries == 0:
            raise ReceiptGatewayError("timed out")

        user = payment.order.customer.user
        send_mail(
            subject=f"Recibo da encomenda #{order_id}",
            message=(
                f"Olá {user.get_username()},\n\n"
                f"Recebemos {payment.amount} € pela encomenda #{order_id}.\n\nLoja DWFA"
            ),
            from_email=None,  # DEFAULT_FROM_EMAIL
            recipient_list=[user.email],
        )
        payment.receipt_sent_at = timezone.now()
        payment.save(update_fields=["receipt_sent_at"])
    return "sent"


@shared_task(bind=True)
def export_orders_report(self, user_id: int, customer_id: int | None) -> dict:
    """Relatório das encomendas de um cliente (todas, se customer_id for None: gestor).

    Vai publicando o progresso com update_state; o GET /api/v1/tasks/<id>/ lê-o.
    """
    qs = Order.objects.all()
    if customer_id is not None:
        qs = qs.filter(customer_id=customer_id)
    qs = qs.annotate(total=Sum(F("items__quantity") * F("items__unit_price"))).order_by("id")
    total_orders = qs.count()
    amount = Decimal("0")
    by_status: dict[str, int] = {}

    for i, order in enumerate(qs.iterator(), start=1):
        amount += order.total or Decimal("0")
        by_status[order.status] = by_status.get(order.status, 0) + 1
        time.sleep(settings.REPORT_STEP_SECONDS)  # faz de trabalho a sério
        self.update_state(state="PROGRESS", meta={"current": i, "total": total_orders})

    # O resultado vai em JSON para o Redis: o Decimal segue como texto (nunca float).
    return {"orders": total_orders, "amount": str(amount), "by_status": by_status}
