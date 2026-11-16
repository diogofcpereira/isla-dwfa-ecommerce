"""Tarefas Celery da loja (Ficha 05).

Três regras: ids, nunca objetos (a mensagem é JSON e a linha pode ter mudado);
idempotentes (o broker entrega pelo menos uma vez); enfileiradas depois do commit.
"""

from smtplib import SMTPException

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Payment


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
