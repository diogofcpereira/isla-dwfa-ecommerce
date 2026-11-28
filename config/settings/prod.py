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

# M2 (extra): os emails das entregas. Por omissão vão para a consola, ou seja, para
# `docker compose logs backend` (o compose local não tem servidor de email). Num deploy a
# sério: EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend e o servidor no .env.
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

# Os logs vão para a consola: `docker compose logs backend` mostra-os.
# Ficha 06: o LOGGING é o de base.py (uma linha de JSON por evento, LOG_JSON=true por omissão);
# este ficheiro deixou de ter o seu, que escrevia só a mensagem e perdia os campos.
