"""Recurso Diogo: a entrega de uma encomenda paga.

O gestor agenda a entrega e vai-a atualizando (agendada → em trânsito → entregue);
o cliente acompanha as entregas das suas encomendas. Ao concluir a entrega, a
encomenda passa a "entregue" (Order.Status.DELIVERED).
"""

from django.db import models
from django.db.models import Q


class Delivery(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Agendada"
        IN_TRANSIT = "in_transit", "Em trânsito"
        DELIVERED = "delivered", "Entregue"

    # OneToOne: uma encomenda tem no máximo uma entrega.
    # PROTECT: não se apaga uma encomenda que já tem entrega marcada.
    order = models.OneToOneField("shop.Order", on_delete=models.PROTECT, related_name="delivery")
    status = models.CharField(max_length=12, choices=Status, default=Status.SCHEDULED)
    scheduled_for = models.DateTimeField()
    address = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_for"]
        constraints = [
            # Entregue ⇔ tem data de entrega: a base de dados não aceita um sem o outro.
            models.CheckConstraint(
                condition=(
                    Q(status="delivered", delivered_at__isnull=False)
                    | (~Q(status="delivered") & Q(delivered_at__isnull=True))
                ),
                name="ck_delivery_delivered_at_matches_status",
            ),
        ]
        indexes = [
            # A agenda do gestor: entregas por estado, ordenadas por data.
            models.Index(fields=["status", "scheduled_for"], name="ix_delivery_status_date"),
        ]

    def __str__(self):
        return f"Entrega da encomenda #{self.order_id}"
