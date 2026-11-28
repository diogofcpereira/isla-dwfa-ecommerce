"""Ficha 06 · Passo 1: o middleware de medição e o formato JSON dos logs."""

import json
import logging
import sys

import pytest
from rest_framework.test import APIClient

from core.logs import JsonFormatter

pytestmark = pytest.mark.django_db


def test_every_request_gets_server_timing_and_a_request_id(caplog):
    caplog.set_level(logging.INFO, logger="drivenow.request")
    r = APIClient().get("/api/v1/cars/")
    assert r.status_code == 200
    assert r["Server-Timing"].startswith("app;dur=") and 'queries"' in r["Server-Timing"]
    record = next(rec for rec in caplog.records if rec.name == "drivenow.request")
    assert record.view == "car-list" and record.status == 200 and record.user_id is None
    assert record.db_queries >= 1 and record.request_id == r["X-Request-ID"]


def test_the_request_id_from_the_proxy_is_kept():
    r = APIClient().get("/api/v1/cars/", HTTP_X_REQUEST_ID="abc123")
    assert r["X-Request-ID"] == "abc123"


def test_health_check_is_not_measured(caplog):
    caplog.set_level(logging.INFO, logger="drivenow.request")
    r = APIClient().get("/api/health/")
    assert "Server-Timing" not in r
    assert not [rec for rec in caplog.records if rec.name == "drivenow.request"]


def test_json_formatter_turns_extra_into_fields():
    record = logging.makeLogRecord(
        {"name": "drivenow.request", "levelname": "INFO", "msg": "request", "db_queries": 3}
    )
    line = json.loads(JsonFormatter().format(record))
    assert line["event"] == "request" and line["db_queries"] == 3 and line["level"] == "INFO"
    try:
        raise ValueError("falhou")
    except ValueError:
        record.exc_info = sys.exc_info()
    assert "ValueError: falhou" in json.loads(JsonFormatter().format(record))["exception"]
