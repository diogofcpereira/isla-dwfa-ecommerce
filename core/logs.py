"""Logs estruturados · structured logs (Aula 09).

Uma linha de JSON por evento, para o stdout. Em produção quem lê os logs é uma
máquina (Loki, Elasticsearch, CloudWatch): campos com nome pesquisam-se e agregam-se;
frases não. Sem dependências — o `logging` da biblioteca-padrão chega.
"""

import json
import logging
from datetime import UTC, datetime

# atributos que qualquer LogRecord tem · attributes every LogRecord carries
_STANDARD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        # tudo o que veio em `extra={...}` passa a campo · whatever came in `extra` is a field
        for key, value in record.__dict__.items():
            if key not in _STANDARD and not key.startswith("_"):
                event[key] = value
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, default=str)
