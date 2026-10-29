# shop/tests/test_security.py
"""Testes do hardening (Ficha 03, Parte 3)."""
import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

SPA = "http://localhost:5173"


@pytest.fixture
def api():
    return APIClient()


# ---------- CORS ----------

def test_cors_preflight_allows_the_spa(api):
    r = api.options("/api/v1/orders/",
                    HTTP_ORIGIN=SPA,
                    HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
                    HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization")
    assert r.status_code == 200                       # o preflight não pede token
    assert r["Access-Control-Allow-Origin"] == SPA


def test_cors_ignores_unknown_origins(api):
    r = api.options("/api/v1/orders/",
                    HTTP_ORIGIN="http://evil.example",
                    HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET")
    assert "Access-Control-Allow-Origin" not in r     # o browser bloqueia a leitura


# ---------- Força bruta: throttling no login ----------

@pytest.mark.django_db
def test_login_is_throttled_after_10_attempts(api):
    body = {"username": "ninguem", "password": "errada"}
    for _ in range(10):
        r = api.post("/api/v1/auth/token/", body, format="json")
        assert r.status_code == 401                   # credenciais erradas
    r = api.post("/api/v1/auth/token/", body, format="json")
    assert r.status_code == 429                       # 11.ª tentativa: Too Many Requests


# ---------- Passwords ----------

def test_password_needs_at_least_12_characters():
    with pytest.raises(ValidationError):
        validate_password("Curta#2026")               # 10 caracteres
    validate_password("uma-frase-bem-longa-2026")     # passa: não levanta erro