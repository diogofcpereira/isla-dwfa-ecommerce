"""Produção · production (Aula 08: deploy)."""

from .base import *  # noqa: F403
from .base import env

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# CORS: CORS_ALLOWED_ORIGINS vem do base.py (lido do .env; por omissão http://localhost:5173).
# Em produção, define a variável de ambiente com a origem real da SPA.

# Cabeçalhos de segurança · security headers
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # HTTP → HTTPS
SESSION_COOKIE_SECURE = True             # cookie de sessão só viaja por HTTPS
CSRF_COOKIE_SECURE = True                # cookie CSRF só viaja por HTTPS
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # HSTS: o browser só usa HTTPS durante 30 dias
SECURE_HSTS_INCLUDE_SUBDOMAINS = True    # ... também nos subdomínios
SECURE_HSTS_PRELOAD = True               # Ficha 03 · Parte 3: resolve o aviso security.W021
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")