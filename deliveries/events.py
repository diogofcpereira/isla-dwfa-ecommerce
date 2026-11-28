"""Ficha 06 · Parte 3 (opção B): os eventos de negócio das entregas, em log estruturado.

Com LOG_JSON=true cada evento é uma linha de JSON, com campos que se pesquisam:
    {"event": "delivery_shipped", "delivery_id": 12, "order_id": 40, "status": "in_transit",
     "user_id": 1, ...}
As views chamam log_delivery_event com transaction.on_commit: só se regista o que ficou
gravado (um 409 ou um rollback não deixam um evento de algo que não aconteceu).
Nos logs vão ids. Nomes, emails, moradas e tokens nunca: a morada da entrega fica de fora.
"""

import logging

logger = logging.getLogger("drivenow.deliveries")


def log_delivery_event(event, delivery, user):
    logger.info(
        event,
        extra={
            "delivery_id": delivery.pk,
            "order_id": delivery.order_id,
            "status": delivery.status,
            "user_id": user.pk,
        },
    )
