"""Desenvolvimento local · local development."""

from .base import *  # noqa: F403
from .base import env

DEBUG = env("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Email para a consola em dev · email to the console in dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Ficha 06: em desenvolvimento os logs leem-se melhor como texto; LOG_JSON=true no .env
# mostra o JSON (os campos view, status, duration_ms, db_queries e db_ms).
if not env.bool("LOG_JSON", default=False):
    LOGGING["handlers"]["console"]["formatter"] = "text"  # noqa: F405
