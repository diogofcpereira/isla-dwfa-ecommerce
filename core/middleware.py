"""Ficha 06: uma linha por pedido, com quanto demorou e quantas queries fez.

Copiado de aula-09/core/middleware.py (dwfa-2627-solucoes), sem as duas linhas da métrica
REQUEST_DB_QUERIES: o grupo escolheu o log estruturado (Parte 3, opção B).

Mede cada pedido (duração total, número de queries e tempo na base de dados) e:
  1. escreve uma linha de log estruturada (core.logs.JsonFormatter com LOG_JSON=true);
  2. devolve o cabeçalho Server-Timing (no browser: DevTools → Network → Timing);
  3. devolve o X-Request-ID, o id que aparece na linha de log desse pedido.
Funciona com DEBUG=False: usa connection.execute_wrapper, não connection.queries.
"""

import logging
import uuid
from time import perf_counter

from django.db import connection

logger = logging.getLogger("drivenow.request")

# Ruído: o health check dos contentores (de 10 em 10 s) e um eventual /metrics.
SKIP = ("/api/health/", "/metrics")


class QueryCounter:
    """Embrulha cada query desta ligação: conta-a e soma o tempo que demorou."""

    def __init__(self):
        self.count = 0
        self.seconds = 0.0

    def __call__(self, execute, sql, params, many, context):
        start = perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            self.count += 1
            self.seconds += perf_counter() - start


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(SKIP):
            return self.get_response(request)
        # O id vem do proxy se ele o mandar; senão nasce aqui.
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.request_id = request_id
        counter = QueryCounter()
        start = perf_counter()
        with connection.execute_wrapper(counter):
            response = self.get_response(request)
        duration_ms = (perf_counter() - start) * 1000
        db_ms = counter.seconds * 1000
        match = request.resolver_match
        view = (match.view_name if match else None) or "unresolved"
        user = getattr(request, "user", None)
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "view": view,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 1),
                "db_queries": counter.count,
                "db_ms": round(db_ms, 1),
                # O id, nunca o email nem o nome: os logs não são sítio para dados pessoais.
                "user_id": user.pk if user is not None and user.is_authenticated else None,
            },
        )
        response["X-Request-ID"] = request_id
        response["Server-Timing"] = (
            f'app;dur={duration_ms:.1f}, db;dur={db_ms:.1f};desc="{counter.count} queries"'
        )
        return response
