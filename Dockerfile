# syntax=docker/dockerfile:1
# Dockerfile — a imagem de produção da API (Django + Gunicorn), em duas fases.
# Fase 1 (build): instala as dependências com o uv e recolhe os ficheiros estáticos.
# Fase 2 (runtime): só o Python, o .venv e o código — sem uv, sem cache, sem ferramentas.

# ---------- fase 1: build ----------
FROM python:3.13-slim AS build

# O uv vem de uma imagem oficial, com a versão fixa (a mesma família do uv.lock).
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Primeiro só as dependências: enquanto o pyproject.toml e o uv.lock não mudarem,
# esta camada vem da cache e um rebuild depois de mudar código demora segundos.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Depois o código (o .dockerignore deixa de fora .env, .venv, frontend/, testes de cache…).
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Os estáticos do admin e do Swagger, recolhidos já na imagem (valores só para o build:
# o collectstatic não abre a base de dados, mas os settings exigem estas variáveis).
RUN DJANGO_SETTINGS_MODULE=config.settings.prod \
    SECRET_KEY=build-only-not-a-secret \
    ALLOWED_HOSTS=localhost \
    DATABASE_URL=postgres://build:build@localhost:5432/build \
    /app/.venv/bin/python manage.py collectstatic --noinput

# ---------- fase 2: runtime ----------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# Extra do M2 (segurança da imagem): as correções de segurança do Debian publicadas desde que
# a imagem base foi gerada, e sem o pip, que não é preciso em runtime (as dependências vêm no
# .venv) e traz bibliotecas antigas embutidas. O Trivy, no CI, confirma o resultado.
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && /usr/local/bin/python -m pip uninstall -y pip

# Um utilizador sem privilégios: se alguém explorar a app, não é root no contentor.
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app
COPY --from=build --chown=app:app /app /app
USER app

EXPOSE 8000

# Ao arrancar: copia os estáticos para o volume partilhado com o Nginx (fica sempre
# atualizado depois de um rebuild) e arranca o Gunicorn. As migrações correm-se à mão:
#   docker compose -f compose.prod.yaml exec backend python manage.py migrate
CMD ["sh", "-c", "python manage.py collectstatic --noinput -v 0 && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --access-logfile - --error-logfile -"]