"""Recurso do Rúben: a marcação de um test drive.

O cliente pede um horário para experimentar uma viatura; o gestor confirma ou
recusa; o cliente pode cancelar enquanto o pedido estiver ativo. Os horários são
de hora a hora e cada viatura só tem uma marcação ativa por horário.
"""

from django.db import models
from django.db.models import Q


class TestDrive(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Pedido"
        CONFIRMED = "confirmed", "Confirmado"
        DECLINED = "declined", "Recusado"
        CANCELLED = "cancelled", "Cancelado"

    # Estados que ocupam o horário da viatura.
    ACTIVE = [Status.REQUESTED, Status.CONFIRMED]

    # PROTECT: uma viatura com marcações não se apaga (retira-se com is_active=False).
    car = models.ForeignKey("shop.Car", on_delete=models.PROTECT, related_name="test_drives")
    customer = models.ForeignKey(
        "shop.Customer", on_delete=models.CASCADE, related_name="test_drives"
    )
    scheduled_for = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status, default=Status.REQUESTED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_for"]
        constraints = [
            # Só uma marcação ativa por viatura e horário; as recusadas e canceladas libertam-no.
            models.UniqueConstraint(
                fields=["car", "scheduled_for"],
                condition=Q(status__in=["requested", "confirmed"]),
                name="uq_testdrive_car_slot_active",
            ),
        ]
        indexes = [
            models.Index(fields=["car", "scheduled_for"], name="ix_testdrive_car_date"),
        ]

    def __str__(self):
        return f"Test drive de {self.car} em {self.scheduled_for:%d/%m %H:%M}"
