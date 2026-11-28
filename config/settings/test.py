"""Testes (pytest-django) · tests."""

from .base import *  # noqa: F403

DEBUG = False

# Hasher rápido: os testes não medem a força das passwords · fast hasher: tests do not
# benchmark password strength
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Ficha 06: texto nos testes (o JSON tem o seu próprio teste em core/tests/test_ficha06.py).
LOGGING["handlers"]["console"]["formatter"] = "text"  # noqa: F405
