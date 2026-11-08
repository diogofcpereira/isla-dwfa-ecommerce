"""Erros da API no formato da RFC 9457 (Problem Details for HTTP APIs).

Todas as respostas de erro da API ficam com a mesma forma, com o Content-Type
`application/problem+json`:

    {
      "type": "about:blank",
      "title": "Not Found",
      "status": 404,
      "detail": "Não encontrado.",
      "instance": "/api/v1/orders/99/"
    }

Os erros de validação (400) juntam o membro de extensão `errors`, com o erro de
cada campo: {"errors": {"quantity": ["Só há 2 em stock."]}}.
"""

from http import HTTPStatus

from rest_framework.views import exception_handler

VALIDATION_DETAIL = "O pedido tem dados inválidos."


def problem_details_handler(exc, context):
    # 1.º o DRF trata a exceção como sempre (códigos, cabeçalhos como o Retry-After).
    response = exception_handler(exc, context)
    if response is None:
        # Não é um erro da API (ex.: um bug): o Django responde 500, sem traceback em prod.
        return None

    status = response.status_code
    data = response.data
    problem = {
        "type": "about:blank",  # RFC 9457: sem página própria, o título é o do código HTTP
        "title": HTTPStatus(status).phrase,
        "status": status,
        "instance": context["request"].path,
    }
    if isinstance(data, dict) and "detail" in data:
        # Erro simples (401, 403, 404, 405, 409, 429...): a mensagem vai para "detail"
        # e o resto (ex.: "code" e "messages" do simplejwt) fica como extensão.
        problem["detail"] = str(data["detail"])
        problem.update({key: value for key, value in data.items() if key != "detail"})
        codes = exc.get_codes() if hasattr(exc, "get_codes") else None
        if isinstance(codes, str):
            problem.setdefault("code", codes)
    else:
        # Erro de validação: um dicionário por campo (ou uma lista de erros gerais).
        problem["detail"] = VALIDATION_DETAIL
        problem["errors"] = data

    response.data = problem
    response.content_type = "application/problem+json"
    return response
