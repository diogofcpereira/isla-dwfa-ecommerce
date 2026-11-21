"""Produção · production (Aula 08: deploy).

M2: a mesma configuração corre no `docker compose -f compose.prod.yaml up` local, que é
HTTP simples (http://localhost). As regras que exigem HTTPS ficam ligadas por omissão e
só se desligam com DJANGO_HTTPS=False — um esquecimento nunca deixa produção sem HTTPS.
"""

from .base import *  # noqa: F403
from .base import env

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# CORS: CORS_ALLOWED_ORIGINS vem do base.py (lido do .env; por omissão http://localhost:5173).
# Com o Nginx a servir a SPA e a API na mesma origem, o browser nem faz pedidos CORS.

# O Nginx está à frente: diz-nos se o pedido original veio por HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cabeçalhos de segurança · security headers
HTTPS = env.bool("DJANGO_HTTPS", default=True)  # M2: False só no compose local (HTTP)
SECURE_SSL_REDIRECT = HTTPS  # HTTP → HTTPS
SESSION_COOKIE_SECURE = HTTPS  # cookie de sessão só viaja por HTTPS
CSRF_COOKIE_SECURE = HTTPS  # cookie CSRF só viaja por HTTPS
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30 if HTTPS else 0  # HSTS: só HTTPS durante 30 dias
SECURE_HSTS_INCLUDE_SUBDOMAINS = HTTPS  # ... também nos subdomínios
SECURE_HSTS_PRELOAD = HTTPS  # Ficha 03 · Parte 3: resolve o aviso security.W021

# Os logs vão para a consola: `docker compose logs backend` mostra-os.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
