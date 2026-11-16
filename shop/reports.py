"""Ficha 05 · Parte 2: um trabalho longo responde 202 Accepted e expõe o progresso.

POST /api/v1/reports/orders/ → 202 + {"id", "status_url"} + Location (a view só enfileira)
GET  /api/v1/tasks/<id>/     → {"id", "state", "progress", "result", "error"}
"""

from celery.result import AsyncResult
from django.core.cache import cache
from django.urls import reverse
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Customer
from .permissions import is_gestor
from .tasks import export_orders_report

OWNER_TTL = 3600  # segundos: o mesmo tempo que o resultado fica no Redis


def owner_key(task_id: str) -> str:
    return f"task:{task_id}:owner"


class OrdersReportView(APIView):
    """Enfileira o relatório e responde logo. Quem pede fica registado como dono."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={
            202: inline_serializer(
                name="TaskAccepted",
                fields={"id": serializers.CharField(), "status_url": serializers.CharField()},
            )
        },
    )
    def post(self, request):
        user = request.user
        if is_gestor(user):
            customer_id = None  # o gestor vê todas as encomendas
        else:
            # Como no perform_create das encomendas: quem ainda não tem perfil ganha um
            # (e o relatório sai vazio).
            customer, _ = Customer.objects.get_or_create(user=user)
            customer_id = customer.id

        result = export_orders_report.delay(user.id, customer_id)
        # Um id de tarefa é uma capacidade: guardamos quem a pediu, para mais ninguém a ler.
        cache.set(owner_key(result.id), user.id, OWNER_TTL)

        url = reverse("task-status", args=[result.id])
        return Response({"id": result.id, "status_url": url}, status=202, headers={"Location": url})


class TaskStatusView(APIView):
    """O estado de uma tarefa. Só o dono (ou um gestor); para os outros, a tarefa não existe."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="TaskStatus",
                fields={
                    "id": serializers.CharField(),
                    "state": serializers.CharField(),
                    "progress": serializers.DictField(allow_null=True),
                    "result": serializers.DictField(allow_null=True),
                    "error": serializers.CharField(allow_null=True),
                },
            ),
            404: OpenApiResponse(description="Tarefa desconhecida, expirada ou de outro."),
        }
    )
    def get(self, request, task_id: str):
        owner = cache.get(owner_key(task_id))
        # Desconhecida, expirada e alheia dão a MESMA resposta: não se confirma que existe.
        if owner is None or (owner != request.user.id and not is_gestor(request.user)):
            raise NotFound("Tarefa não encontrada.")

        res = AsyncResult(task_id)
        state = res.state  # PENDING → PROGRESS → SUCCESS (ou FAILURE)
        info = res.info  # o meta durante o PROGRESS, o valor devolvido no SUCCESS
        return Response(
            {
                "id": task_id,
                "state": state,
                "progress": info if state == "PROGRESS" else None,
                "result": info if state == "SUCCESS" else None,
                "error": str(info) if state == "FAILURE" else None,
            }
        )
