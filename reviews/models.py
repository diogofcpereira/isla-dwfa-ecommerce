"""Recurso do Filipe: a avaliação de uma viatura por quem a comprou.

O cliente avalia (nota de 1 a 5 e um comentário); a avaliação fica pendente até
o gestor a moderar (aprovada ou oculta). O público só vê as aprovadas.
"""

from django.db import models
from django.db.models import Q


class Review(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        APPROVED = "approved", "Aprovada"
        HIDDEN = "hidden", "Oculta"

    # CASCADE: uma avaliação não faz sentido sem a viatura ou sem o cliente que a escreveu.
    car = models.ForeignKey("shop.Car", on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey("shop.Customer", on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Uma avaliação por cliente e viatura: quem quer mudar de opinião edita a sua.
            models.UniqueConstraint(fields=["car", "customer"], name="uq_review_car_customer"),
            models.CheckConstraint(
                condition=Q(rating__gte=1, rating__lte=5), name="ck_review_rating_1_5"
            ),
        ]
        indexes = [
            # A página de uma viatura mostra as avaliações aprovadas dela.
            models.Index(fields=["car", "status"], name="ix_review_car_status"),
        ]

    def __str__(self):
        return f"{self.rating}★ para {self.car} por {self.customer}"
