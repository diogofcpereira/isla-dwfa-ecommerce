"""M2 (extra do Diogo): o cliente recebe um email em cada passo da entrega.

Agendada (com a data e a morada), saiu do stand e entregue. As views chamam-no com
transaction.on_commit: o email só sai depois de a mudança estar gravada, por isso um
pedido que falha (400, 409) ou é desfeito nunca avisa o cliente de algo que não aconteceu.
Um servidor de email em baixo não pode estragar a resposta da API: o erro fica no log.
"""

import logging

from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)

MESSAGES = {
    "scheduled": (
        "A entrega da encomenda #{order} foi agendada",
        "A entrega da sua encomenda #{order} ficou agendada para {when}, na morada:\n{address}",
    ),
    "shipped": (
        "A encomenda #{order} saiu do stand",
        "A sua encomenda #{order} está a caminho de:\n{address}\nData prevista: {when}.",
    ),
    "delivered": (
        "A encomenda #{order} foi entregue",
        "A sua encomenda #{order} foi entregue em {delivered}.\n"
        "Já pode avaliar a viatura em Avaliações, na sua conta.",
    ),
}


def when(moment):
    """27/11/2026 às 10:30, na hora de Lisboa (TIME_ZONE)."""
    return timezone.localtime(moment).strftime("%d/%m/%Y às %H:%M")


def notify_customer(delivery, event):
    """Envia o email do `event` ao dono da encomenda. Devolve True se o enviou."""
    user = delivery.order.customer.user
    if not user.email:
        return False
    subject, body = MESSAGES[event]
    values = {
        "order": delivery.order_id,
        "when": when(delivery.scheduled_for),
        "address": delivery.address,
        "delivered": when(delivery.delivered_at) if delivery.delivered_at else "",
    }
    greeting = f"Olá {user.first_name or user.username},\n\n"
    try:
        send_mail(
            subject.format(**values),
            greeting + body.format(**values) + "\n\nDriveNow",
            None,  # DEFAULT_FROM_EMAIL
            [user.email],
        )
    except Exception:
        logger.exception("Email da entrega %s (%s) não enviado.", delivery.pk, event)
        return False
    return True
